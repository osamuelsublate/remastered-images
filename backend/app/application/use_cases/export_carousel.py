"""Use case: render the FINAL deliverables for the download zip.

For each slide, decides the export format:

- MP4 when the slide contains a user video block or is flagged to animate
  (``motion.animate``) — what Instagram needs for mixed carousels.
- Composited PNG (1080x1350, text + blocks burned in via Remotion
  ``renderStill``) for static slides — unlike the raw ``slides/*.png``
  backgrounds, these contain the full layered composition.

Runs as a background job (same pattern as ``animate_slides``) with per-slide
``export_status`` progress; the results land in ``<cid>/exports/`` which
``download_carousel`` zips up.
"""

from __future__ import annotations

import logging

from ...domain.carousel import CarouselState, Slide
from ...domain.errors import (
    CarouselNotFound,
    GenerationInProgress,
    NoPlanYet,
)
from ...ports.carousel_repository import CarouselRepository
from ...ports.job_runner import JobRunner
from ...ports.media_storage import MediaStorage
from ...ports.video_renderer import VideoRenderer
from ...prompts import build_motion_props

logger = logging.getLogger(__name__)


def slide_export_ext(slide: Slide) -> str:
    """"mp4" when the slide has motion or a video block; "png" otherwise."""
    has_video_block = any(
        el.type == "video" and el.media_url for el in slide.elements
    )
    animates = slide.motion is not None and slide.motion.animate
    return "mp4" if (has_video_block or animates) else "png"


def export_carousel(
    cid: str,
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
        raise NoPlanYet("Nenhum plano para exportar.")
    if job_runner.is_active(cid):
        raise GenerationInProgress("Geração já em andamento.")

    for slide in state.plan.slides:
        slide.export_status = "pending"
        slide.export_error = None
    state.status = "rendering"
    state.error = None
    repo.save(state)

    indices = [s.index for s in state.plan.slides]

    def _run() -> None:
        for idx in indices:
            current = repo.load(cid)
            if current is None or current.plan is None:
                return
            cur = current.plan.slides[idx - 1]
            cur.export_status = "running"
            cur.export_error = None
            repo.save(current)

            try:
                total_slides = len(current.plan.slides)
                props = build_motion_props(
                    current.plan, cur, total_slides, image_origin=media_origin
                )
                ext = slide_export_ext(cur)
                out_path = media_storage.export_output_path(cid, idx, ext)
                # Drop a stale export in the other format (e.g. a slide that
                # had a video block and no longer does).
                other = media_storage.export_output_path(
                    cid, idx, "png" if ext == "mp4" else "mp4"
                )
                other.unlink(missing_ok=True)
                if ext == "mp4":
                    video_renderer.render(props, out_path)
                else:
                    video_renderer.render_still(props, out_path)
                cur.export_status = "done"
            except Exception as exc:  # noqa: BLE001
                logger.exception("Export of slide %d failed", idx)
                cur.export_status = "error"
                cur.export_error = str(exc)

            latest = repo.load(cid)
            if latest is not None and latest.plan is not None:
                latest.plan.slides[idx - 1] = cur
                repo.save(latest)

        final = repo.load(cid)
        if final is None or final.plan is None:
            return
        if any(s.export_status == "error" for s in final.plan.slides):
            final.status = "error"
            final.error = "Falha ao exportar um ou mais slides."
        else:
            statuses = [s.status for s in final.plan.slides]
            final.status = "done" if all(s == "done" for s in statuses) else "planned"
        repo.save(final)

    started = job_runner.submit(cid, _run)
    if not started:
        raise GenerationInProgress("Geração já em andamento.")

    result = repo.load(cid)
    if result is None:
        raise CarouselNotFound(cid)
    return result
