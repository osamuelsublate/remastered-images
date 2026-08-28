import pytest

from app.adapters.storage.local_media_storage import LocalMediaStorage
from app.application.use_cases.create_carousel import create_carousel
from app.application.use_cases.replace_slide_image import replace_slide_image
from app.domain.errors import CarouselNotFound, InvalidSlideSelection, NoPlanYet

from tests.application.test_plan_carousel import _make_plan
from tests.fakes import FakeCarouselRepository


def _seed_planned_carousel():
    repo = FakeCarouselRepository()
    state = create_carousel(repo=repo)
    state.plan = _make_plan(None)
    repo.save(state)
    return repo, state.id


def test_replace_slide_image_writes_file_and_updates_slide(tmp_path):
    repo, cid = _seed_planned_carousel()
    media_storage = LocalMediaStorage(tmp_path)

    result = replace_slide_image(cid, 1, b"uploaded-bytes", repo=repo, media_storage=media_storage)

    slide = result.plan.slides[0]
    assert slide.status == "done"
    assert slide.error is None
    assert slide.image_url is not None
    assert (tmp_path / cid / "slides" / "slide-01.png").read_bytes() == b"uploaded-bytes"


def test_replace_slide_image_raises_when_carousel_missing(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    with pytest.raises(CarouselNotFound):
        replace_slide_image("does-not-exist", 1, b"x", repo=repo, media_storage=media_storage)


def test_replace_slide_image_raises_without_plan(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    state = create_carousel(repo=repo)
    with pytest.raises(NoPlanYet):
        replace_slide_image(state.id, 1, b"x", repo=repo, media_storage=media_storage)


def test_replace_slide_image_raises_on_invalid_index(tmp_path):
    repo, cid = _seed_planned_carousel()
    media_storage = LocalMediaStorage(tmp_path)
    with pytest.raises(InvalidSlideSelection):
        replace_slide_image(cid, 99, b"x", repo=repo, media_storage=media_storage)
