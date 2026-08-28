"""Use case: content-aware text placement over a freshly generated background.

Runs inside the generation job, right after a slide's image is written and
before the slide is marked ``done``:

1. measure the real image (``domain.image_metrics`` — edge-density/luminance
   grid);
2. ask the layout-vision agent for artistic placements
   (``TextAIProvider.suggest_text_layout``), anchored by the metrics grid;
3. if the vision call fails, fall back to the deterministic calmest-region
   search (``domain.layout_refine.fallback_placements``);
4. validate everything mathematically (clamps, height estimation, overlap
   resolution, WCAG contrast) and apply to the slide's auto-managed elements
   by their deterministic ids (``s{i}-h1`` / ``s{i}-body`` /
   ``s{i}-swipe_cue``).

Never raises: any unexpected failure keeps the default role-based layout and
logs — a slide with default text placement beats a failed generation.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ...domain.carousel import CarouselPlan, Slide
from ...domain.image_metrics import analyze_slide_image, metrics_prompt_block
from ...domain.layout_refine import (
    TextPlacement,
    fallback_placements,
    validate_placements,
)
from ...ports.text_ai_provider import TextAIProvider

logger = logging.getLogger(__name__)

_TARGET_TO_ID_SUFFIX = {"h1": "h1", "body": "body", "swipe_cue": "swipe_cue"}


def _apply_placements(slide: Slide, placements: list[TextPlacement]) -> None:
    by_id = {el.id: el for el in slide.elements}
    for p in placements:
        element = by_id.get(f"s{slide.index}-{_TARGET_TO_ID_SUFFIX[p.target]}")
        if element is None:
            continue
        element.rect.x = round(p.x, 2)
        element.rect.y = round(p.y, 2)
        element.rect.w = round(p.w, 2)
        element.rect.h = round(max(p.h, 4.0), 2)
        element.style.font_size = p.font_size
        element.style.align = p.align
        element.style.color = p.color


def refine_slide_layout(
    slide: Slide,
    image_path: Path,
    plan: CarouselPlan,
    total: int,
    *,
    text_ai: TextAIProvider,
) -> None:
    """Reposition the slide's automatic text blocks over the actual generated
    image. Mutates ``slide.elements`` in place; swallows all errors."""
    try:
        metrics = analyze_slide_image(image_path)
    except Exception:  # noqa: BLE001
        logger.exception("Image analysis failed for slide %d; keeping default layout", slide.index)
        return

    palette = plan.art_direction.palette
    text_color = next(
        (c.hex for c in palette if "text" in c.role.lower()), "#ffffff"
    )

    try:
        placements = text_ai.suggest_text_layout(
            image_png=image_path.read_bytes(),
            metrics_block=metrics_prompt_block(metrics),
            slide=slide,
            art_direction=plan.art_direction,
            total=total,
        )
        # An empty/absurd answer is as useless as an API failure.
        if not any(p.target == "h1" for p in placements):
            raise ValueError("layout vision returned no h1 placement")
    except Exception:  # noqa: BLE001
        logger.warning(
            "Layout vision failed for slide %d; using deterministic fallback",
            slide.index,
            exc_info=True,
        )
        placements = fallback_placements(slide, metrics, text_color)

    try:
        validate_placements(placements, slide, metrics, palette)
        _apply_placements(slide, placements)
    except Exception:  # noqa: BLE001
        logger.exception(
            "Placement validation failed for slide %d; keeping default layout", slide.index
        )
