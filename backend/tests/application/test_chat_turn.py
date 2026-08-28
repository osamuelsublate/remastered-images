import pytest

from app.application.use_cases.chat_turn import begin_chat_turn, stream_chat_reply
from app.application.use_cases.create_carousel import create_carousel
from app.domain.errors import CarouselNotFound, GenerationInProgress

from tests.application.test_plan_carousel import _make_plan
from tests.fakes import FakeCarouselRepository, FakeTextAIProvider, SyncJobRunner


def test_chat_turn_appends_messages_without_plan():
    repo = FakeCarouselRepository()
    text_ai = FakeTextAIProvider(chat_factory=lambda *a, **k: ("oi!", None))
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)

    begun = begin_chat_turn(state.id, "quero um carrossel", repo=repo, job_runner=job_runner)
    events = list(stream_chat_reply(begun, repo=repo, text_ai=text_ai))

    assert [kind for kind, _ in events] == ["delta", "done"]
    final = events[-1][1]
    assert [m.content for m in final.messages[-2:]] == ["quero um carrossel", "oi!"]
    assert final.status == "draft"


def test_chat_turn_adopts_proposed_plan():
    repo = FakeCarouselRepository()
    plan = _make_plan(None)
    text_ai = FakeTextAIProvider(chat_factory=lambda *a, **k: ("pronto", plan))
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)

    begun = begin_chat_turn(state.id, "manda ver", repo=repo, job_runner=job_runner)
    events = list(stream_chat_reply(begun, repo=repo, text_ai=text_ai))

    final = events[-1][1]
    assert final.plan is not None
    assert final.status == "planned"


def test_chat_turn_raises_when_generation_active():
    repo = FakeCarouselRepository()
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)
    job_runner._active.add(state.id)  # simulate an in-flight generation job

    with pytest.raises(GenerationInProgress):
        begin_chat_turn(state.id, "oi", repo=repo, job_runner=job_runner)


def test_chat_turn_raises_when_carousel_missing():
    repo = FakeCarouselRepository()
    job_runner = SyncJobRunner()

    with pytest.raises(CarouselNotFound):
        begin_chat_turn("does-not-exist", "oi", repo=repo, job_runner=job_runner)


def test_chat_turn_emits_error_event_on_provider_failure():
    repo = FakeCarouselRepository()

    def _boom(*args, **kwargs):
        raise RuntimeError("provider down")

    text_ai = FakeTextAIProvider(chat_factory=_boom)
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)

    begun = begin_chat_turn(state.id, "oi", repo=repo, job_runner=job_runner)
    events = list(stream_chat_reply(begun, repo=repo, text_ai=text_ai))

    assert events[-1][0] == "error"
    assert "provider down" in events[-1][1]
    # The user's message was still recorded even though the reply failed.
    assert repo.load(state.id).messages[-1].content == "oi"
