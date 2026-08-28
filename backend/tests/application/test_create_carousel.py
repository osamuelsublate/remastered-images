from app.application.use_cases.create_carousel import create_carousel

from tests.fakes import FakeCarouselRepository


def test_create_carousel_starts_in_draft_with_greeting():
    repo = FakeCarouselRepository()

    state = create_carousel(repo=repo)

    assert state.status == "draft"
    assert state.id
    assert len(state.messages) == 1
    assert state.messages[0].role == "assistant"
    assert state.messages[0].content

    # Persisted, not just returned.
    assert repo.load(state.id) is not None
