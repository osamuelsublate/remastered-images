"""Port for speech-to-text (voice input dictation in the chat).

Kept separate from ``TextAIProvider`` since it is a different kind of AI
capability (audio in, text out) with its own model/adapter, even though the
current adapter happens to also use OpenAI.
"""

from __future__ import annotations

from typing import Iterator, Protocol


class TranscriptionStream(Protocol):
    """Streamed result of one transcription.

    Iterating yields transcript text deltas as they arrive; once the
    iterator is exhausted, ``result()`` returns the final full transcript.
    """

    def __iter__(self) -> Iterator[str]: ...

    def result(self) -> str: ...


class AudioTranscriptionProvider(Protocol):
    def transcribe_stream(self, audio_bytes: bytes, filename: str) -> TranscriptionStream: ...
