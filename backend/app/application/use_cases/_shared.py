"""Helpers shared by ``generate_images`` and ``regenerate_slides``."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from ...ports.carousel_repository import CarouselRepository
from ...ports.image_ai_provider import ImageAIProvider
from ...ports.media_storage import MediaStorage
from ...ports.text_ai_provider import TextAIProvider
from ...prompts import build_image_prompt
from .refine_slide_layout import refine_slide_layout

logger = logging.getLogger(__name__)


def render_one_slide(
    cid: str,
    idx: int,
    total: int,
    *,
    repo: CarouselRepository,
    media_storage: MediaStorage,
    image_ai: ImageAIProvider,
    references: list[Path] | None,
    quality: str,
    refinement: str = "",
    self_reference: bool = False,
    text_ai: TextAIProvider | None = None,
) -> None:
    """Generate a single slide image, persisting status before and after.

    When ``self_reference`` is set (selective regeneration), we edit the
    slide's own existing image instead of the uploaded references: the
    revision just needs to keep that slide's look and change what was asked —
    sending the whole reference set again is unnecessary and much slower.

    When ``text_ai`` is provided, the slide's text blocks are repositioned
    over the actual generated image (content-aware placement) before the
    slide is marked ``done`` — so the frontend never shows the default
    layout on a fresh image.
    """
    state = repo.load(cid)
    if state is None or state.plan is None:
        return
    cur = state.plan.slides[idx - 1]
    cur.status = "running"
    cur.error = None
    repo.save(state)

    output_path = media_storage.slide_output_path(cid, idx, "png")
    refs = references
    if self_reference:
        refs = [output_path] if output_path.exists() else None

    try:
        prompt = build_image_prompt(state.plan, cur, total, refinement=refinement)
        image_ai.generate_slide_image(
            prompt=prompt,
            output_path=output_path,
            references=refs or None,
            quality=quality,
        )
        if text_ai is not None:
            refine_slide_layout(cur, output_path, state.plan, total, text_ai=text_ai)
        cur.status = "done"
        # Cache-busting token: the file path is reused on regeneration, so
        # without a changing query param the browser (and React) would keep
        # showing the previously cached image.
        cur.image_url = (
            media_storage.public_url(cid, output_path.name) + f"?v={int(time.time() * 1000)}"
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Slide %d failed", idx)
        cur.status = "error"
        cur.error = str(exc)

    latest = repo.load(cid)
    if latest is not None and latest.plan is not None:
        latest.plan.slides[idx - 1] = cur
        repo.save(latest)


def finalize_status(cid: str, repo: CarouselRepository) -> None:
    final = repo.load(cid)
    if final is None or final.plan is None:
        return
    statuses = [s.status for s in final.plan.slides]
    if any(s == "error" for s in statuses):
        final.status = "error"
    elif all(s == "done" for s in statuses):
        final.status = "done"
    else:
        final.status = "planned"
    repo.save(final)
