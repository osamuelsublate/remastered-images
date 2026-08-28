"""Use case: attach reference images uploaded for a carousel."""

from __future__ import annotations

from ...domain.carousel import CarouselState
from ...domain.errors import CarouselNotFound
from ...ports.carousel_repository import CarouselRepository
from ...ports.media_storage import MediaStorage


def upload_references(
    cid: str,
    files: list[tuple[str, bytes]],
    *,
    repo: CarouselRepository,
    media_storage: MediaStorage,
) -> CarouselState:
    state = repo.load(cid)
    if state is None:
        raise CarouselNotFound(cid)

    saved: list[str] = list(state.references)
    for filename, data in files:
        if not filename:
            continue
        media_storage.save_reference(cid, filename, data)
        safe_name = filename.replace("/", "_")
        if safe_name not in saved:
            saved.append(safe_name)
    state.references = saved
    repo.save(state)
    return state
