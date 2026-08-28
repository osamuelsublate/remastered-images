"""FastAPI application: carousel studio backend.

Only wiring lives here: create the app, map domain errors to HTTP status
codes, include the routes, and mount static media + the built frontend.
All business logic lives in ``application/use_cases``.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .api import deps
from .api.routes.carousels import router as carousels_router
from .api.routes.transcriptions import router as transcriptions_router
from .domain.errors import (
    CarouselNotFound,
    GenerationInProgress,
    InvalidSlideSelection,
    NoPlanYet,
    NoSlidesGenerated,
    PlanningFailed,
    UnsupportedMediaType,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Carousel Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Domain error -> HTTP status mapping (single place, instead of a
# try/except HTTPException block repeated in every route).
# ---------------------------------------------------------------------------

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    CarouselNotFound: 404,
    NoSlidesGenerated: 404,
    GenerationInProgress: 409,
    NoPlanYet: 400,
    InvalidSlideSelection: 400,
    UnsupportedMediaType: 415,
    PlanningFailed: 502,
}


def _make_handler(status_code: int):
    async def _handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return _handler


for _exc_type, _status_code in _STATUS_BY_ERROR.items():
    app.add_exception_handler(_exc_type, _make_handler(_status_code))


app.include_router(carousels_router)
app.include_router(transcriptions_router)


# ---------------------------------------------------------------------------
# Static: generated media + (optional) frontend build
# ---------------------------------------------------------------------------

app.mount("/media", StaticFiles(directory=str(deps.get_media_storage().media_root())), name="media")

_frontend_dist = config.REPO_ROOT / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
