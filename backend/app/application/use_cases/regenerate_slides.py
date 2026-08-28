"""Use case: regenerate a selection of slides, optionally revising their copy."""

from __future__ import annotations

import logging

from ...domain.carousel import CarouselState
from ...domain.errors import (
    CarouselNotFound,
    GenerationInProgress,
    InvalidSlideSelection,
    NoPlanYet,
)
from ...domain.layout_defaults import fonts_for, patch_slide_elements_content
from ...ports.carousel_repository import CarouselRepository
from ...ports.image_ai_provider import ImageAIProvider
from ...ports.job_runner import JobRunner
from ...ports.media_storage import MediaStorage
from ...ports.text_ai_provider import TextAIProvider
from ._shared import finalize_status, render_one_slide

logger = logging.getLogger(__name__)


def regenerate_slides(
    cid: str,
    indices: list[int],
    instruction: str,
    *,
    repo: CarouselRepository,
    media_storage: MediaStorage,
    text_ai: TextAIProvider,
    image_ai: ImageAIProvider,
    job_runner: JobRunner,
    # Content-aware text placement over the regenerated image (the image
    # changes, so the old placement may no longer fit it).
    refine_layout: bool = True,
) -> CarouselState:
    state = repo.load(cid)
    if state is None:
        raise CarouselNotFound(cid)
    if state.plan is None:
        raise NoPlanYet("Nenhum plano para regerar.")
    if job_runner.is_active(cid):
        raise GenerationInProgress("Geração já em andamento.")

    total = len(state.plan.slides)
    valid_indices = sorted({i for i in indices if 1 <= i <= total})
    if not valid_indices:
        raise InvalidSlideSelection("Nenhum slide válido selecionado.")

    # Mark selected slides as pending synchronously so the UI shows progress
    # immediately. Keep the old image_url so the card doesn't flash empty.
    for idx in valid_indices:
        slide = state.plan.slides[idx - 1]
        slide.status = "pending"
        slide.error = None
    state.status = "generating"
    state.error = None
    repo.save(state)

    def _run() -> None:
        current = repo.load(cid)
        if current is None or current.plan is None:
            return

        # Optionally revise copy/visual of the selected slides from the note.
        if instruction.strip():
            try:
                revisions = text_ai.revise_slides(current.plan, valid_indices, instruction)
                total_for_patch = len(current.plan.slides)
                heading_font, body_font = fonts_for(current.plan.art_direction)
                for s in current.plan.slides:
                    revision = revisions.get(s.index)
                    if revision is not None:
                        s.headline = revision.headline
                        s.body = revision.body
                        s.visual_prompt = revision.visual_prompt
                        s.swipe_cue = revision.swipe_cue
                        # Patch only the content of the matching-role element
                        # (creating it from the default layout if the user
                        # had deleted it) — preserves any rect/style the user
                        # already customized manually in the editor.
                        patch_slide_elements_content(
                            s,
                            plan_handle=current.plan.handle,
                            total=total_for_patch,
                            palette=current.plan.art_direction.palette,
                            heading_font=heading_font,
                            body_font=body_font,
                        )
                repo.save(current)
            except Exception:  # noqa: BLE001
                logger.exception("revise_slides failed; regenerating with current copy")
                current = repo.load(cid)
                if current is None or current.plan is None:
                    return

        total_slides = len(current.plan.slides)
        quality = current.quality
        for idx in valid_indices:
            render_one_slide(
                cid,
                idx,
                total_slides,
                repo=repo,
                media_storage=media_storage,
                image_ai=image_ai,
                references=None,
                quality=quality,
                refinement=instruction,
                self_reference=True,
                text_ai=text_ai if refine_layout else None,
            )

        finalize_status(cid, repo)

    started = job_runner.submit(cid, _run)
    if not started:
        raise GenerationInProgress("Geração já em andamento.")

    result = repo.load(cid)
    if result is None:
        raise CarouselNotFound(cid)
    return result
