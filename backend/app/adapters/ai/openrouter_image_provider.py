"""OpenRouter-backed ``ImageAIProvider``.

Slide backgrounds go through **chat completions** with
``modalities: ["image", "text"]`` (OpenRouter has no ``/images/edits``
endpoint, so reference-based editing only works this way; Gemini image
models accept reference images inline in the message). The primary model can
be safety-trigger-happy, so a fallback model is tried automatically when the
primary refuses or returns no image.

Isolated block assets keep using OpenRouter's ``/images/generations``
passthrough with an OpenAI ``gpt-image-*`` model — the only family that
supports ``background="transparent"``.

The returned image's resolution depends on the routed model (e.g. 4:5 at
928x1152 on Gemini), so the slide is normalized here — cover-resize to the
exact configured ``image_size`` — keeping the downstream contract (Remotion,
layout refine, zip export) identical to the previous provider's.
"""

from __future__ import annotations

import base64
import io
import logging
import time
from math import gcd
from pathlib import Path

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise ImportError("Pillow is required: pip install Pillow") from exc

logger = logging.getLogger(__name__)

MAX_BYTES = 4 * 1024 * 1024
MAX_RETRIES = 5
INITIAL_BACKOFF = 2.0
IMAGE_TIMEOUT = 900.0  # seconds per image request. Editing with several
# reference images legitimately takes minutes; a short timeout would kill an
# in-progress edit and restart it from scratch.

# Aspect ratios the Gemini image family accepts via ``image_config``.
_SUPPORTED_RATIOS = {
    "1:1": 1 / 1, "2:3": 2 / 3, "3:2": 3 / 2, "3:4": 3 / 4, "4:3": 4 / 3,
    "4:5": 4 / 5, "5:4": 5 / 4, "9:16": 9 / 16, "16:9": 16 / 9, "21:9": 21 / 9,
}


class _NoImageReturned(RuntimeError):
    """The model answered without an image (refusal / content filter)."""


class OpenRouterImageProvider:
    def __init__(
        self,
        api_key: str | None,
        model: str,
        image_size: str,
        default_quality: str,
        asset_model: str = "openai/gpt-image-1",
        fallback_model: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._fallback_model = fallback_model
        self._image_size = image_size
        self._default_quality = default_quality
        self._asset_model = asset_model
        self._base_url = base_url
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "OPENROUTER_API_KEY não configurada. Crie um .env a partir de .env.example."
                )
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                default_headers={
                    "HTTP-Referer": "http://localhost:5173",
                    "X-Title": "Carousel Studio",
                },
            )
        return self._client

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def _target_size(self) -> tuple[int, int]:
        w, h = self._image_size.lower().split("x")
        return int(w), int(h)

    @property
    def _aspect_ratio(self) -> str:
        """Closest Gemini-supported aspect ratio for the configured size."""
        w, h = self._target_size
        d = gcd(w, h)
        exact = f"{w // d}:{h // d}"
        if exact in _SUPPORTED_RATIOS:
            return exact
        ratio = w / h
        return min(_SUPPORTED_RATIOS, key=lambda k: abs(_SUPPORTED_RATIOS[k] - ratio))

    @staticmethod
    def _reference_data_url(path: Path) -> str:
        """Reference image as a data URL, recompressed under the size cap."""
        raw = path.read_bytes()
        suffix = path.suffix.lower().lstrip(".") or "png"
        if len(raw) <= MAX_BYTES:
            mime = {"jpg": "jpeg"}.get(suffix, suffix)
            return f"data:image/{mime};base64,{base64.b64encode(raw).decode()}"

        img = Image.open(path).convert("RGB")
        if max(img.size) > 2048:
            img.thumbnail((2048, 2048), Image.LANCZOS)
        quality = 90
        buf = io.BytesIO()
        while quality >= 40:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            if buf.tell() <= MAX_BYTES:
                break
            quality -= 10
        return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"

    def _normalize_to_target(self, png: bytes) -> bytes:
        """Cover-resize (center crop) the model output to the exact size."""
        tw, th = self._target_size
        img = Image.open(io.BytesIO(png)).convert("RGB")
        if img.size != (tw, th):
            scale = max(tw / img.width, th / img.height)
            img = img.resize(
                (round(img.width * scale), round(img.height * scale)), Image.LANCZOS
            )
            left = (img.width - tw) // 2
            top = (img.height - th) // 2
            img = img.crop((left, top, left + tw, top + th))
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()

    @staticmethod
    def _retryable_call(fn):
        backoff = INITIAL_BACKOFF
        last_exc: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return fn()
            except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
                last_exc = exc
                logger.warning(
                    "%s (attempt %d/%d). Waiting %.0fs…",
                    type(exc).__name__,
                    attempt,
                    MAX_RETRIES,
                    backoff,
                )
            except APIStatusError as exc:
                if exc.status_code and exc.status_code >= 500:
                    last_exc = exc
                    logger.warning(
                        "API %d (attempt %d/%d). Waiting %.0fs…",
                        exc.status_code,
                        attempt,
                        MAX_RETRIES,
                        backoff,
                    )
                else:
                    raise
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        raise RuntimeError(
            f"Falhou após {MAX_RETRIES} tentativas. Último erro: {last_exc}"
        ) from last_exc

    def _chat_image_call(
        self, model: str, prompt: str, reference_urls: list[str]
    ) -> bytes:
        """One chat-completions image generation/edit; returns raw PNG bytes."""
        client = self._get_client().with_options(timeout=IMAGE_TIMEOUT)
        content: list[dict] = [{"type": "text", "text": prompt}]
        content.extend(
            {"type": "image_url", "image_url": {"url": url}} for url in reference_urls
        )

        def _call():
            return client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                extra_body={
                    "modalities": ["image", "text"],
                    "image_config": {"aspect_ratio": self._aspect_ratio},
                },
            )

        response = self._retryable_call(_call)
        data = response.model_dump()
        choice = data["choices"][0]
        images = choice["message"].get("images") or []
        if not images:
            raise _NoImageReturned(
                f"O modelo {model} não retornou imagem "
                f"(finish_reason={choice.get('finish_reason')!r})."
            )
        url = images[0]["image_url"]["url"]
        return base64.b64decode(url.split(",", 1)[1])

    # ------------------------------------------------------------------
    # ImageAIProvider port
    # ------------------------------------------------------------------

    def generate_slide_image(
        self,
        *,
        prompt: str,
        output_path: Path,
        references: list[Path] | None = None,
        quality: str | None = None,
    ) -> None:
        """Generate one slide image and save it as PNG.

        ``quality`` is accepted for port compatibility; the Gemini image
        family has no quality knob, so it is ignored here.
        """
        reference_urls = [self._reference_data_url(p) for p in references or []]
        models = [self._model]
        if self._fallback_model and self._fallback_model != self._model:
            models.append(self._fallback_model)

        last_exc: Exception | None = None
        for model in models:
            try:
                png = self._chat_image_call(model, prompt, reference_urls)
                break
            except _NoImageReturned as exc:
                last_exc = exc
                logger.warning("%s — tentando fallback…", exc)
        else:
            raise RuntimeError(
                f"Nenhum modelo de imagem retornou resultado. Último erro: {last_exc}"
            ) from last_exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self._normalize_to_target(png))

    def generate_asset_image(
        self,
        *,
        prompt: str,
        output_path: Path,
        quality: str | None = None,
    ) -> None:
        """Generate one isolated block asset (icon/illustration) as a PNG
        with a transparent background, via the ``/images/generations``
        passthrough (gpt-image family only)."""
        client = self._get_client().with_options(timeout=IMAGE_TIMEOUT)

        def _call():
            return client.images.generate(
                model=self._asset_model,
                prompt=prompt,
                size="1024x1024",
                quality=quality or self._default_quality,
                background="transparent",
                output_format="png",
                n=1,
            )

        response = self._retryable_call(_call)
        b64 = response.data[0].b64_json
        if b64 is None:
            raise RuntimeError("A API não retornou b64_json.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(b64))
