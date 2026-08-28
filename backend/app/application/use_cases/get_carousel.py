"""Use case: load the current state of a carousel."""

from __future__ import annotations

from ...domain.carousel import CarouselState
from ...domain.errors import CarouselNotFound
from ...ports.carousel_repository import CarouselRepository


def get_carousel(cid: str, *, repo: CarouselRepository) -> CarouselState:
    state = repo.load(cid)
    if state is None:
        raise CarouselNotFound(cid)
    return state
