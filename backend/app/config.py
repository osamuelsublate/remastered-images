"""Central configuration for the carousel studio backend.

``load_settings()`` reads the environment (populated from ``.env`` at import
time) into an immutable ``Settings`` object. It is called exactly once per
process by ``api/deps.get_settings`` (cached); tests override the individual
``api/deps`` provider functions instead of mutating the environment after
the fact.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Repo root is two levels up from this file (backend/app/config.py -> repo/).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = Path(__file__).resolve().parent.parent

# Load .env from the repo root (where the OPENROUTER_API_KEY lives).
load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    planning_model: str
    chat_model: str
    transcription_model: str
    image_model: str
    image_fallback_model: str
    image_size: str
    default_quality: str
    asset_image_model: str
    layout_refine_enabled: bool
    carousels_dir: Path
    remotion_dir: Path
    remotion_render_script: Path
    node_bin: str
    motion_fps: int
    render_timeout: int
    media_origin: str
    openrouter_api_key: str | None
    openrouter_base_url: str


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("DATA_DIR", BACKEND_ROOT / "data"))
    carousels_dir = data_dir / "carousels"
    carousels_dir.mkdir(parents=True, exist_ok=True)
    remotion_dir = Path(os.environ.get("REMOTION_DIR", REPO_ROOT / "remotion"))

    return Settings(
        # Planning/revision need more structural quality (full carousel
        # structure + art direction via a tool call); chat replies are
        # short conversational turns and don't need the flagship model.
        # Model ids are OpenRouter-style ("author/model").
        planning_model=os.environ.get("PLANNING_MODEL", "openai/gpt-5.5"),
        # gpt-5.5 has no "-mini" sibling yet; gpt-5.4-mini is the closest
        # cost-effective option for conversational chat replies.
        chat_model=os.environ.get("CHAT_MODEL", "openai/gpt-5.4-mini"),
        # OpenRouter's transcriptions passthrough does not stream; the
        # provider emits the transcript in a single delta (see
        # OpenRouterAudioTranscriptionProvider).
        transcription_model=os.environ.get(
            "TRANSCRIPTION_MODEL", "openai/gpt-4o-mini-transcribe"
        ),
        # Slide backgrounds via chat completions (modalities: image). Nano
        # Banana Pro is the highest-quality option; its safety filter is
        # touchy, so a Flash fallback keeps generation resilient.
        image_model=os.environ.get("IMAGE_MODEL", "google/gemini-3-pro-image"),
        image_fallback_model=os.environ.get(
            "IMAGE_FALLBACK_MODEL", "google/gemini-3.1-flash-image"
        ),
        # Instagram carousel is 1080x1350 (4:5). The Gemini image family
        # returns its own 4:5 resolution (e.g. 928x1152); the provider
        # cover-resizes the result to this exact size.
        image_size=os.environ.get("IMAGE_SIZE", "1088x1360"),
        default_quality=os.environ.get("IMAGE_QUALITY", "medium"),
        # Isolated block assets (icons/illustrations) generated from the
        # editor's "Criar imagem" action need a transparent background —
        # only the gpt-image family supports that, via OpenRouter's
        # /images/generations passthrough (gpt-image-1.5 is not listed on
        # OpenRouter; gpt-image-1 is the closest available).
        asset_image_model=os.environ.get("ASSET_IMAGE_MODEL", "openai/gpt-image-1"),
        # Content-aware text placement: after each background is generated,
        # a vision agent + image metrics reposition h1/body over the real
        # image. Disable to keep the deterministic role-based default layout.
        layout_refine_enabled=os.environ.get("LAYOUT_REFINE", "true").strip().lower()
        not in ("0", "false", "no", "off"),
        carousels_dir=carousels_dir,
        remotion_dir=remotion_dir,
        remotion_render_script=remotion_dir / "render.mjs",
        node_bin=os.environ.get("NODE_BIN", "node"),
        motion_fps=int(os.environ.get("MOTION_FPS", "30")),
        # Per-clip render timeout (seconds). A short clip is fast, but the
        # first run may also download a headless browser.
        render_timeout=int(os.environ.get("RENDER_TIMEOUT", "600")),
        # Origin a headless Chromium uses to fetch the slide PNG from our
        # /media mount.
        media_origin=os.environ.get("MEDIA_ORIGIN", "http://127.0.0.1:8000"),
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY"),
        openrouter_base_url=os.environ.get(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ),
    )
