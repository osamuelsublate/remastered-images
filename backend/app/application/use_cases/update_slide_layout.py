"""Use case: persist a manual layout edit (drag/resize/style) for one slide.

Synchronous, no ``job_runner`` — this is plain data persistence, called
(debounced) on every editor interaction, not a long-running AI/render job.
"""

from __future__ import annotations

from ...domain.carousel import CarouselState, ElementRect, SlideElement
from ...domain.errors import CarouselNotFound, InvalidSlideSelection, NoPlanYet
from ...ports.carousel_repository import CarouselRepository


def update_slide_layout(
    cid: str,
    index: int,
    *,
    background_rect: ElementRect | None,
    elements: list[SlideElement] | None,
    repo: CarouselRepository,
) -> CarouselState:
    state = repo.load(cid)
    if state is None:
        raise CarouselNotFound(cid)
    if state.plan is None:
        raise NoPlanYet("Nenhum plano para editar.")

    total = len(state.plan.slides)
    if not (1 <= index <= total):
        raise InvalidSlideSelection("Slide inválido.")

    slide = state.plan.slides[index - 1]
    if background_rect is not None:
        slide.background_rect = background_rect
    if elements is not None:
        slide.elements = elements

    repo.save(state)
    return state
