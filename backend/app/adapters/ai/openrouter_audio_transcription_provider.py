"""OpenRouter-backed ``AudioTranscriptionProvider``: speech-to-text.

OpenRouter's ``/audio/transcriptions`` passthrough accepts the same
multipart payload as OpenAI's (webm/opus straight from the browser's
MediaRecorder works), but it does NOT stream — ``stream=True`` is ignored
and the full transcript comes back in one JSON response. To keep the
``TranscriptionStream`` port (and the SSE contract with the frontend)
intact, the whole transcript is emitted as a single delta.
"""

from __future__ import annotations

import io
from typing import Iterator

from openai import OpenAI


class _SingleShotTranscriptionStream:
    """Satisfies ``TranscriptionStream`` with one non-streaming API call.

    Building this has no side effects; the request only starts once the
    object is iterated.
    """

    def __init__(
        self,
        client: OpenAI,
        *,
        model: str,
        audio_bytes: bytes,
        filename: str,
    ) -> None:
        self._client = client
        self._model = model
        self._audio_bytes = audio_bytes
        self._filename = filename
        self._final_text: str | None = None

    def __iter__(self) -> Iterator[str]:
        buf = io.BytesIO(self._audio_bytes)
        buf.name = self._filename
        transcription = self._client.audio.transcriptions.create(
            model=self._model,
            file=buf,
        )
        self._final_text = transcription.text or ""
        if self._final_text:
            yield self._final_text

    def result(self) -> str:
        if self._final_text is None:
            raise RuntimeError("O stream ainda não foi iterado até o fim.")
        return self._final_text


class OpenRouterAudioTranscriptionProvider:
    def __init__(
        self,
        api_key: str | None,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        self._api_key = api_key
        self._model = model
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

    def transcribe_stream(
        self, audio_bytes: bytes, filename: str
    ) -> _SingleShotTranscriptionStream:
        return _SingleShotTranscriptionStream(
            self._get_client(),
            model=self._model,
            audio_bytes=audio_bytes,
            filename=filename,
        )
