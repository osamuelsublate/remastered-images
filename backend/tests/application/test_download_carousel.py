import zipfile
from io import BytesIO

import pytest

from app.adapters.storage.local_media_storage import LocalMediaStorage
from app.application.use_cases.create_carousel import create_carousel
from app.application.use_cases.download_carousel import download_carousel
from app.domain.errors import CarouselNotFound, NoSlidesGenerated

from tests.application.test_plan_carousel import _make_plan
from tests.fakes import FakeCarouselRepository


def test_download_carousel_raises_when_no_slides(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    state = create_carousel(repo=repo)

    with pytest.raises(NoSlidesGenerated):
        download_carousel(state.id, repo=repo, media_storage=media_storage)


def test_download_carousel_raises_when_missing(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)

    with pytest.raises(CarouselNotFound):
        download_carousel("does-not-exist", repo=repo, media_storage=media_storage)


def test_download_carousel_bundles_slides_and_caption(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    state = create_carousel(repo=repo)
    plan = _make_plan(None)
    state.plan = plan
    repo.save(state)
    slide_path = media_storage.slide_output_path(state.id, 1, "png")
    slide_path.write_bytes(b"fake-png")

    zip_bytes, filename = download_carousel(state.id, repo=repo, media_storage=media_storage)

    assert filename == f"carousel-{state.id}.zip"
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert "slide-01.png" in names
        assert "caption.txt" in names
        caption = zf.read("caption.txt").decode("utf-8")
        assert plan.caption in caption
        assert "#a" in caption


def test_download_carousel_prefers_final_exports_over_raw_slides(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    state = create_carousel(repo=repo)
    state.plan = _make_plan(None)
    repo.save(state)
    # Raw background (no text burned in) + a final composited export.
    media_storage.slide_output_path(state.id, 1, "png").write_bytes(b"raw-bg")
    media_storage.export_output_path(state.id, 1, "png").write_bytes(b"composited")
    media_storage.export_output_path(state.id, 2, "mp4").write_bytes(b"clip")

    zip_bytes, _ = download_carousel(state.id, repo=repo, media_storage=media_storage)

    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert "slide-01.png" in names
        assert "slide-02.mp4" in names
        assert zf.read("slide-01.png") == b"composited"
