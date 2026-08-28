"""Use case: overwrite a slide's background image with a user upload.

Bypasses the image AI entirely — same idea as ``upload_references``, just
targeting a specific slide's rendered output instead of the reference pool.
"""

from __future__ import annotations

import time

from ...domain.carousel import CarouselState
from ...domain.errors import CarouselNotFound, InvalidSlideSelection, NoPlanYet
from ...ports.carousel_repository import CarouselRepository
from ...ports.media_storage import MediaStorage


def replace_slide_image(
    cid: str,
    index: int,
    data: bytes,
    *,
    repo: CarouselRepository,
    media_storage: MediaStorage,
) -> CarouselState:
    state = repo.load(cid)
    if state is None:
        raise CarouselNotFound(cid)
    if state.plan is None:
        raise NoPlanYet("Nenhum plano para editar.")

    total = len(state.plan.slides)
    if not (1 <= index <= total):
        raise InvalidSlideSelection("Slide inválido.")

    output_path = media_storage.slide_output_path(cid, index, "png")
    output_path.write_bytes(data)

    slide = state.plan.slides[index - 1]
    slide.status = "done"
    slide.error = None
    # Cache-busting token: the file path is reused, so without a changing
    # query param the browser (and React) would keep showing the old image.
    slide.image_url = media_storage.public_url(cid, output_path.name) + f"?v={int(time.time() * 1000)}"

    repo.save(state)
    return state
