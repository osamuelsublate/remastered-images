"""Use case: store a user-uploaded image/video to be used as a slide block.

The file just goes to the carousel's media pool and its public URL is
returned; attaching it to a slide happens through the regular layout PATCH
(the editor inserts an ``image``/``video`` element with this ``media_url``).
"""

from __future__ import annotations

from pathlib import PurePosixPath

from ...domain.errors import CarouselNotFound, UnsupportedMediaType
from ...ports.carousel_repository import CarouselRepository
from ...ports.media_storage import MediaStorage

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}


def upload_block_media(
    cid: str,
    filename: str,
    data: bytes,
    *,
    repo: CarouselRepository,
    media_storage: MediaStorage,
) -> tuple[str, str]:
    """Returns ``(public_url, kind)`` where kind is ``"image"`` or ``"video"``."""
    state = repo.load(cid)
    if state is None:
        raise CarouselNotFound(cid)

    ext = PurePosixPath(filename.lower()).suffix
    if ext in IMAGE_EXTENSIONS:
        kind = "image"
    elif ext in VIDEO_EXTENSIONS:
        kind = "video"
    else:
        raise UnsupportedMediaType(
            "Envie uma imagem (png, jpg, webp, gif) ou vídeo (mp4, mov, webm)."
        )

    if not data:
        raise UnsupportedMediaType("Arquivo vazio.")

    url = media_storage.save_block_media(cid, filename, data)
    return url, kind
