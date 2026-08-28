"""Request DTOs for the carousel API.

Responses are domain models (``domain.carousel.CarouselState``) returned
directly — there is no separate response DTO layer in this pragmatic
hexagonal setup.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..domain.carousel import Brief, CarouselPlan, ElementRect, SlideElement


class PlanRequest(BaseModel):
    brief: Brief


class GenerateRequest(BaseModel):
    plan: CarouselPlan
    quality: str = "medium"


class ChatRequest(BaseModel):
    message: str


class RegenerateRequest(BaseModel):
    indices: list[int]
    instruction: str = ""


class AnimateRequest(BaseModel):
    # Empty = render every slide whose motion.animate is true.
    indices: list[int] = []


class UpdateSlideLayoutRequest(BaseModel):
    """Partial update: only the provided fields are applied. Sent (debounced)
    from the layered editor on every drag/resize/style edit."""

    background_rect: ElementRect | None = None
    elements: list[SlideElement] | None = None


class GenerateBlockImageRequest(BaseModel):
    """"Criar imagem" editor action: a short free-text idea for an isolated,
    transparent-background block asset (icon/illustration)."""

    slide_index: int
    prompt: str
