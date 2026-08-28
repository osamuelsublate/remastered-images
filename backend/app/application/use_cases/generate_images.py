"""Use case: generate all slide images for a carousel plan."""

from __future__ import annotations

from ...domain.carousel import CarouselPlan, CarouselState
from ...domain.errors import CarouselNotFound, GenerationInProgress
from ...ports.carousel_repository import CarouselRepository
from ...ports.image_ai_provider import ImageAIProvider
from ...ports.job_runner import JobRunner
from ...ports.media_storage import MediaStorage
from ...ports.text_ai_provider import TextAIProvider
from ._shared import finalize_status, render_one_slide


def generate_images(
    cid: str,
    plan: CarouselPlan,
    quality: str,
    *,
    repo: CarouselRepository,
    media_storage: MediaStorage,
    image_ai: ImageAIProvider,
    job_runner: JobRunner,
    # When provided, each slide's text layout is refined over the actual
    # generated image (content-aware placement); None disables the step.
    text_ai: TextAIProvider | None = None,
) -> CarouselState:
    state = repo.load(cid)
    if state is None:
        raise CarouselNotFound(cid)
    if job_runner.is_active(cid):
        raise GenerationInProgress("Geração já em andamento.")

    # Persist "generating" + reset slide statuses synchronously, BEFORE the
    # background job starts, so the response (and the frontend polling) sees
    # the correct status immediately instead of racing the worker.
    for slide in plan.slides:
        slide.status = "pending"
        slide.image_url = None
        slide.error = None
    state.plan = plan
    state.quality = quality
    state.status = "generating"
    state.error = None
    repo.save(state)

    def _run() -> None:
        references = media_storage.list_reference_paths(cid)
        total = len(plan.slides)
        for slide in plan.slides:
            render_one_slide(
                cid,
                slide.index,
                total,
                repo=repo,
                media_storage=media_storage,
                image_ai=image_ai,
                references=references,
                quality=quality,
                text_ai=text_ai,
            )
        finalize_status(cid, repo)

    started = job_runner.submit(cid, _run)
    if not started:
        raise GenerationInProgress("Geração já em andamento.")

    result = repo.load(cid)
    if result is None:
        raise CarouselNotFound(cid)
    return result
