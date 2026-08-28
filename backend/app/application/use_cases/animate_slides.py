"""Use case: render short animated clips for a selection of slides."""

from __future__ import annotations

import logging
import time

from ...domain.carousel import CarouselState
from ...domain.errors import (
    CarouselNotFound,
    GenerationInProgress,
    InvalidSlideSelection,
    NoPlanYet,
)
from ...ports.carousel_repository import CarouselRepository
from ...ports.job_runner import JobRunner
from ...ports.media_storage import MediaStorage
from ...ports.video_renderer import VideoRenderer
from ...prompts import build_motion_props
from ._shared import finalize_status

logger = logging.getLogger(__name__)


def animate_slides(
    cid: str,
    indices: list[int],
    *,
    repo: CarouselRepository,
    media_storage: MediaStorage,
    video_renderer: VideoRenderer,
    job_runner: JobRunner,
    media_origin: str,
) -> CarouselState:
    state = repo.load(cid)
    if state is None:
        raise CarouselNotFound(cid)
    if state.plan is None:
        raise NoPlanYet("Nenhum plano para animar.")
    if job_runner.is_active(cid):
        raise GenerationInProgress("Geração já em andamento.")

    total = len(state.plan.slides)
    if indices:
        valid_indices = sorted({i for i in indices if 1 <= i <= total})
    else:
        # Default: every slide the planner flagged to animate.
        valid_indices = [
            s.index for s in state.plan.slides if s.motion is not None and s.motion.animate
        ]
    if not valid_indices:
        raise InvalidSlideSelection("Nenhum slide marcado para animar.")

    # image-mode clips need the rendered PNG as a base.
    for idx in valid_indices:
        slide = state.plan.slides[idx - 1]
        if slide.motion is not None and slide.motion.mode == "image" and not slide.image_url:
            raise InvalidSlideSelection(f"Gere a imagem do slide {idx} antes de animá-lo.")

    for idx in valid_indices:
        slide = state.plan.slides[idx - 1]
        slide.motion_status = "pending"
        slide.motion_error = None
    state.status = "rendering"
    state.error = None
    repo.save(state)

    def _run() -> None:
        for idx in valid_indices:
            current = repo.load(cid)
            if current is None or current.plan is None:
                return
            cur = current.plan.slides[idx - 1]
            cur.motion_status = "running"
            cur.motion_error = None
            repo.save(current)

            try:
                total_slides = len(current.plan.slides)
                props = build_motion_props(
                    current.plan, cur, total_slides, image_origin=media_origin
                )
                out_path = media_storage.slide_output_path(cid, idx, "mp4")
                video_renderer.render(props, out_path)
                cur.motion_status = "done"
                cur.video_url = (
                    media_storage.public_url(cid, out_path.name)
                    + f"?v={int(time.time() * 1000)}"
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Motion render for slide %d failed", idx)
                cur.motion_status = "error"
                cur.motion_error = str(exc)

            latest = repo.load(cid)
            if latest is not None and latest.plan is not None:
                latest.plan.slides[idx - 1] = cur
                repo.save(latest)

        finalize_status(cid, repo)

    started = job_runner.submit(cid, _run)
    if not started:
        raise GenerationInProgress("Geração já em andamento.")

    result = repo.load(cid)
    if result is None:
        raise CarouselNotFound(cid)
    return result
