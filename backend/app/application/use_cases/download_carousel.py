"""Use case: package generated slides + caption into a downloadable zip."""

from __future__ import annotations

import io
import zipfile

from ...domain.errors import CarouselNotFound, NoSlidesGenerated
from ...ports.carousel_repository import CarouselRepository
from ...ports.media_storage import MediaStorage


def download_carousel(
    cid: str,
    *,
    repo: CarouselRepository,
    media_storage: MediaStorage,
) -> tuple[bytes, str]:
    """Returns ``(zip_bytes, download_filename)``.

    Prefers the final composited exports (``exports/`` — PNG with text/blocks
    burned in, MP4 for video slides) produced by ``export_carousel``. Falls
    back to the raw generated slide files for carousels that were never
    exported (older sessions).
    """
    state = repo.load(cid)
    if state is None:
        raise CarouselNotFound(cid)

    files = media_storage.list_export_files(cid) or media_storage.list_slide_files(cid)
    if not files:
        raise NoSlidesGenerated()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, arcname=p.name)
        if state.plan is not None:
            caption = state.plan.caption + "\n\n" + " ".join(
                f"#{h.lstrip('#')}" for h in state.plan.hashtags
            )
            zf.writestr("caption.txt", caption)
    buf.seek(0)
    return buf.getvalue(), f"carousel-{cid}.zip"
