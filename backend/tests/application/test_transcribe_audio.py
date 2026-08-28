from app.application.use_cases.transcribe_audio import transcribe_audio

from tests.fakes import FakeAudioTranscriptionProvider


def test_transcribe_audio_yields_deltas_then_done():
    provider = FakeAudioTranscriptionProvider(chunks=["ola", " mundo"])

    events = list(
        transcribe_audio(b"fake-audio", "clip.webm", transcription_ai=provider)
    )

    assert events == [("delta", "ola"), ("delta", " mundo"), ("done", "ola mundo")]
    assert provider.calls == [(b"fake-audio", "clip.webm")]


def test_transcribe_audio_emits_error_event_on_failure():
    provider = FakeAudioTranscriptionProvider(fail=True)

    events = list(
        transcribe_audio(b"fake-audio", "clip.webm", transcription_ai=provider)
    )

    assert len(events) == 1
    assert events[0][0] == "error"
    assert "transcription provider down" in events[0][1]
