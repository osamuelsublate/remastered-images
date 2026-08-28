"""Voice input: upload a recorded clip, get back a streamed transcript.

Stateless — not tied to any carousel session; the frontend drops the
streamed text straight into the chat textarea for the user to review.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

from ...application.use_cases.transcribe_audio import transcribe_audio
from ...ports.audio_transcription_provider import AudioTranscriptionProvider
from .. import deps
from ..sse import sse_encode

router = APIRouter(prefix="/api")


@router.post("/transcriptions")
async def create_transcription(
    file: UploadFile = File(...),
    transcription_ai: AudioTranscriptionProvider = Depends(deps.get_transcription_ai_provider),
) -> StreamingResponse:
    audio_bytes = await file.read()
    events = transcribe_audio(
        audio_bytes,
        file.filename or "recording.webm",
        transcription_ai=transcription_ai,
    )
    return StreamingResponse(sse_encode(events), media_type="text/event-stream")
