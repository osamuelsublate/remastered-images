"""Use case: generate the initial carousel structure from a brief."""

from __future__ import annotations

from ...domain.carousel import Brief, CarouselState
from ...domain.errors import CarouselNotFound, PlanningFailed
from ...ports.carousel_repository import CarouselRepository
from ...ports.text_ai_provider import TextAIProvider


def plan_carousel(
    cid: str,
    brief: Brief,
    *,
    repo: CarouselRepository,
    text_ai: TextAIProvider,
) -> CarouselState:
    state = repo.load(cid)
    if state is None:
        raise CarouselNotFound(cid)
    try:
        plan = text_ai.plan_carousel(brief)
    except Exception as exc:  # noqa: BLE001
        raise PlanningFailed(f"Falha ao planejar: {exc}") from exc
    state.brief = brief
    state.plan = plan
    state.status = "planned"
    repo.save(state)
    return state
