import pytest

from app.adapters.storage.local_media_storage import LocalMediaStorage
from app.application.use_cases.create_carousel import create_carousel
from app.application.use_cases.upload_block_media import upload_block_media
from app.domain.errors import CarouselNotFound, UnsupportedMediaType

from tests.fakes import FakeCarouselRepository


def test_upload_block_media_stores_image_and_returns_url(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    state = create_carousel(repo=repo)

    url, kind = upload_block_media(
        state.id, "foto.png", b"png-bytes", repo=repo, media_storage=media_storage
    )

    assert kind == "image"
    assert url.startswith(f"/media/{state.id}/media/")
    assert url.endswith("foto.png")
    saved = list((tmp_path / state.id / "media").iterdir())
    assert len(saved) == 1
    assert saved[0].read_bytes() == b"png-bytes"


def test_upload_block_media_detects_video(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    state = create_carousel(repo=repo)

    _, kind = upload_block_media(
        state.id, "clipe.MP4", b"mp4-bytes", repo=repo, media_storage=media_storage
    )

    assert kind == "video"


def test_upload_block_media_rejects_unsupported_extension(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    state = create_carousel(repo=repo)

    with pytest.raises(UnsupportedMediaType):
        upload_block_media(
            state.id, "doc.pdf", b"pdf-bytes", repo=repo, media_storage=media_storage
        )


def test_upload_block_media_rejects_empty_file(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    state = create_carousel(repo=repo)

    with pytest.raises(UnsupportedMediaType):
        upload_block_media(state.id, "foto.png", b"", repo=repo, media_storage=media_storage)


def test_upload_block_media_raises_when_carousel_missing(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)

    with pytest.raises(CarouselNotFound):
        upload_block_media(
            "does-not-exist", "foto.png", b"x", repo=repo, media_storage=media_storage
        )
