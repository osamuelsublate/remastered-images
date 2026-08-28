"""Thin FastAPI routes: parse request -> call use case -> return state.

Business rules and orchestration live in ``application/use_cases``; domain
errors raised there are mapped to HTTP status codes by the exception
handlers registered in ``main.py``.
"""

from __future__ import annotations

import io

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

from ...application.use_cases.animate_slides import animate_slides
from ...application.use_cases.chat_turn import begin_chat_turn, stream_chat_reply
from ...application.use_cases.create_carousel import create_carousel
from ...application.use_cases.download_carousel import download_carousel
from ...application.use_cases.export_carousel import export_carousel
from ...application.use_cases.generate_block_image import generate_block_image
from ...application.use_cases.generate_images import generate_images
from ...application.use_cases.get_carousel import get_carousel
from ...application.use_cases.plan_carousel import plan_carousel
from ...application.use_cases.regenerate_slides import regenerate_slides
from ...application.use_cases.replace_slide_image import replace_slide_image
from ...application.use_cases.update_slide_layout import update_slide_layout
from ...application.use_cases.upload_block_media import upload_block_media
from ...application.use_cases.upload_references import upload_references
from ...domain.carousel import CarouselState
from ...ports.carousel_repository import CarouselRepository
from ...ports.image_ai_provider import ImageAIProvider
from ...ports.job_runner import JobRunner
from ...ports.media_storage import MediaStorage
from ...ports.text_ai_provider import TextAIProvider
from ...ports.video_renderer import VideoRenderer
from .. import deps
from ..schemas import (
    AnimateRequest,
    ChatRequest,
    GenerateBlockImageRequest,
    GenerateRequest,
    PlanRequest,
    RegenerateRequest,
    UpdateSlideLayoutRequest,
)
from ..sse import sse_encode

router = APIRouter(prefix="/api")


@router.get("/health")
def health(settings=Depends(deps.get_settings)) -> dict:
    return {
        "ok": True,
        "planning_model": settings.planning_model,
        "chat_model": settings.chat_model,
        "image_model": settings.image_model,
    }


@router.post("/carousels", response_model=CarouselState)
def create(
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
) -> CarouselState:
    return create_carousel(repo=repo)


@router.get("/carousels/{cid}", response_model=CarouselState)
def get(
    cid: str,
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
) -> CarouselState:
    return get_carousel(cid, repo=repo)


@router.post("/carousels/{cid}/references", response_model=CarouselState)
async def upload_carousel_references(
    cid: str,
    files: list[UploadFile] = File(...),
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
    media_storage: MediaStorage = Depends(deps.get_media_storage),
) -> CarouselState:
    payload = [(f.filename or "", await f.read()) for f in files]
    return upload_references(cid, payload, repo=repo, media_storage=media_storage)


@router.post("/carousels/{cid}/plan", response_model=CarouselState)
def plan(
    cid: str,
    req: PlanRequest,
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
    text_ai: TextAIProvider = Depends(deps.get_text_ai_provider),
) -> CarouselState:
    return plan_carousel(cid, req.brief, repo=repo, text_ai=text_ai)


@router.post("/carousels/{cid}/chat")
def chat(
    cid: str,
    req: ChatRequest,
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
    text_ai: TextAIProvider = Depends(deps.get_text_ai_provider),
    job_runner: JobRunner = Depends(deps.get_job_runner),
) -> StreamingResponse:
    # Validate + record the user's message synchronously, before the
    # StreamingResponse starts — so CarouselNotFound/GenerationInProgress
    # still map to their usual HTTP status codes.
    state = begin_chat_turn(cid, req.message, repo=repo, job_runner=job_runner)
    events = stream_chat_reply(state, repo=repo, text_ai=text_ai)
    return StreamingResponse(sse_encode(events), media_type="text/event-stream")


@router.post("/carousels/{cid}/generate", response_model=CarouselState)
def generate(
    cid: str,
    req: GenerateRequest,
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
    media_storage: MediaStorage = Depends(deps.get_media_storage),
    text_ai: TextAIProvider = Depends(deps.get_text_ai_provider),
    image_ai: ImageAIProvider = Depends(deps.get_image_ai_provider),
    job_runner: JobRunner = Depends(deps.get_job_runner),
    settings=Depends(deps.get_settings),
) -> CarouselState:
    return generate_images(
        cid,
        req.plan,
        req.quality,
        repo=repo,
        media_storage=media_storage,
        image_ai=image_ai,
        job_runner=job_runner,
        text_ai=text_ai if settings.layout_refine_enabled else None,
    )


@router.post("/carousels/{cid}/regenerate", response_model=CarouselState)
def regenerate(
    cid: str,
    req: RegenerateRequest,
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
    media_storage: MediaStorage = Depends(deps.get_media_storage),
    text_ai: TextAIProvider = Depends(deps.get_text_ai_provider),
    image_ai: ImageAIProvider = Depends(deps.get_image_ai_provider),
    job_runner: JobRunner = Depends(deps.get_job_runner),
    settings=Depends(deps.get_settings),
) -> CarouselState:
    return regenerate_slides(
        cid,
        req.indices,
        req.instruction,
        repo=repo,
        media_storage=media_storage,
        text_ai=text_ai,
        image_ai=image_ai,
        job_runner=job_runner,
        refine_layout=settings.layout_refine_enabled,
    )


@router.post("/carousels/{cid}/animate", response_model=CarouselState)
def animate(
    cid: str,
    req: AnimateRequest,
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
    media_storage: MediaStorage = Depends(deps.get_media_storage),
    video_renderer: VideoRenderer = Depends(deps.get_video_renderer),
    job_runner: JobRunner = Depends(deps.get_job_runner),
    settings=Depends(deps.get_settings),
) -> CarouselState:
    return animate_slides(
        cid,
        req.indices,
        repo=repo,
        media_storage=media_storage,
        video_renderer=video_renderer,
        job_runner=job_runner,
        media_origin=settings.media_origin,
    )


@router.patch("/carousels/{cid}/slides/{index}/layout", response_model=CarouselState)
def update_layout(
    cid: str,
    index: int,
    req: UpdateSlideLayoutRequest,
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
) -> CarouselState:
    return update_slide_layout(
        cid,
        index,
        background_rect=req.background_rect,
        elements=req.elements,
        repo=repo,
    )


@router.post("/carousels/{cid}/slides/{index}/image", response_model=CarouselState)
async def replace_image(
    cid: str,
    index: int,
    file: UploadFile = File(...),
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
    media_storage: MediaStorage = Depends(deps.get_media_storage),
) -> CarouselState:
    data = await file.read()
    return replace_slide_image(cid, index, data, repo=repo, media_storage=media_storage)


@router.post("/carousels/{cid}/media")
async def upload_media(
    cid: str,
    file: UploadFile = File(...),
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
    media_storage: MediaStorage = Depends(deps.get_media_storage),
) -> dict:
    data = await file.read()
    url, kind = upload_block_media(
        cid, file.filename or "media", data, repo=repo, media_storage=media_storage
    )
    return {"url": url, "kind": kind}


@router.post("/carousels/{cid}/generate-image")
def generate_image(
    cid: str,
    req: GenerateBlockImageRequest,
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
    media_storage: MediaStorage = Depends(deps.get_media_storage),
    text_ai: TextAIProvider = Depends(deps.get_text_ai_provider),
    image_ai: ImageAIProvider = Depends(deps.get_image_ai_provider),
) -> dict:
    url, kind = generate_block_image(
        cid,
        req.slide_index,
        req.prompt,
        repo=repo,
        media_storage=media_storage,
        text_ai=text_ai,
        image_ai=image_ai,
    )
    return {"url": url, "kind": kind}


@router.post("/carousels/{cid}/export", response_model=CarouselState)
def export(
    cid: str,
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
    media_storage: MediaStorage = Depends(deps.get_media_storage),
    video_renderer: VideoRenderer = Depends(deps.get_video_renderer),
    job_runner: JobRunner = Depends(deps.get_job_runner),
    settings=Depends(deps.get_settings),
) -> CarouselState:
    return export_carousel(
        cid,
        repo=repo,
        media_storage=media_storage,
        video_renderer=video_renderer,
        job_runner=job_runner,
        media_origin=settings.media_origin,
    )


@router.get("/carousels/{cid}/download")
def download(
    cid: str,
    repo: CarouselRepository = Depends(deps.get_carousel_repository),
    media_storage: MediaStorage = Depends(deps.get_media_storage),
) -> StreamingResponse:
    zip_bytes, filename = download_carousel(cid, repo=repo, media_storage=media_storage)
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
