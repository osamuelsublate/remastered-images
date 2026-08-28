"""Port for the text/structure AI provider (copy + carousel structure).

Returns domain types only — provider-specific structured-output shapes
(e.g. the OpenAI ``PlannedCarousel``) are internal adapter details and never
cross this boundary.
"""

from __future__ import annotations

from typing import Iterator, Protocol

from ..domain.carousel import ArtDirection, Brief, CarouselPlan, Slide, SlideRevision
from ..domain.layout_refine import TextPlacement


class ChatTurnStream(Protocol):
    """Streamed result of one chat turn.

    Iterating yields assistant text deltas as they arrive; once the
    iterator is exhausted, ``result()`` returns the final
    ``(full_text, plan_or_none)`` pair (mirrors what the old, non-streaming
    ``chat_turn`` used to return directly).
    """

    def __iter__(self) -> Iterator[str]: ...

    def result(self) -> tuple[str, CarouselPlan | None]: ...


class TextAIProvider(Protocol):
    def plan_carousel(self, brief: Brief) -> CarouselPlan: ...

    def chat_turn_stream(
        self,
        history: list[dict],
        *,
        current_plan: CarouselPlan | None = None,
        references: list[str] | None = None,
    ) -> ChatTurnStream: ...

    def revise_slides(
        self, plan: CarouselPlan, indices: list[int], instruction: str
    ) -> dict[int, SlideRevision]: ...

    def craft_asset_prompt(
        self, user_request: str, *, art_direction: ArtDirection, slide: Slide
    ) -> str:
        """Translate a short, free-text user request into a fully-directed,
        English image-generation prompt for an isolated transparent asset
        (icon/illustration) — see ``ASSET_AGENT_SYSTEM_PROMPT``."""
        ...

    def suggest_text_layout(
        self,
        *,
        image_png: bytes,
        metrics_block: str,
        slide: Slide,
        art_direction: ArtDirection,
        total: int,
    ) -> list[TextPlacement]:
        """Vision agent: given the actual generated background (PNG bytes) and
        its measured metrics grid, propose artistic placements for the slide's
        text blocks — see ``LAYOUT_VISION_SYSTEM_PROMPT``. Raw proposals; the
        caller validates them with ``domain.layout_refine``."""
        ...
