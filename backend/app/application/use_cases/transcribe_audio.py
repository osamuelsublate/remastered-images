"""Use case: transcribe a recorded voice note into text.

Thin pass-through generator — no carousel/session state involved, just
relays the transcription provider's stream so the API layer can forward it
as SSE. Kept as a use case (instead of calling the port directly from the
route) so the route stays a pure "parse request -> call use case" shim,
consistent with the rest of the API layer.
"""

from __future__ import annotations

from typing import Iterator

from ...ports.audio_transcription_provider import AudioTranscriptionProvider

TranscriptionStreamEvent = tuple[str, str]


def transcribe_audio(
    audio_bytes: bytes,
    filename: str,
    *,
    transcription_ai: AudioTranscriptionProvider,
) -> Iterator[TranscriptionStreamEvent]:
    """Yields ``("delta", text)`` chunks, then either ``("done", full_text)``
    once transcription completes, or ``("error", message)`` on failure.
    """
    try:
        streamer = transcription_ai.transcribe_stream(audio_bytes, filename)
        for chunk in streamer:
            yield ("delta", chunk)
        text = streamer.result()
    except Exception as exc:  # noqa: BLE001
        yield ("error", f"Falha na transcrição: {exc}")
        return
    yield ("done", text)
