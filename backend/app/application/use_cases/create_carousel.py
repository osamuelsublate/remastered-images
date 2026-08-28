"""Use case: start a new carousel session with a greeting message."""

from __future__ import annotations

from ...domain.carousel import CarouselState, ChatMessage
from ...ports.carousel_repository import CarouselRepository
from ...prompts import GREETING


def create_carousel(*, repo: CarouselRepository) -> CarouselState:
    state = repo.create(repo.new_id())
    state.messages = [ChatMessage(role="assistant", content=GREETING)]
    repo.save(state)
    return state
