import pytest

from app.adapters.storage.local_media_storage import LocalMediaStorage
from app.application.use_cases.create_carousel import create_carousel
from app.application.use_cases.upload_references import upload_references
from app.domain.errors import CarouselNotFound

from tests.fakes import FakeCarouselRepository


def test_upload_references_saves_files_and_dedupes_names(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    state = create_carousel(repo=repo)

    updated = upload_references(
        state.id,
        [("logo.png", b"first"), ("logo.png", b"second"), ("ref2.jpg", b"third")],
        repo=repo,
        media_storage=media_storage,
    )

    assert sorted(updated.references) == ["logo.png", "ref2.jpg"]
    saved_paths = media_storage.list_reference_paths(state.id)
    assert {p.name for p in saved_paths} == {"logo.png", "ref2.jpg"}
    # The second upload of "logo.png" overwrote the first (same filename).
    assert (tmp_path / state.id / "references" / "logo.png").read_bytes() == b"second"


def test_upload_references_raises_when_carousel_missing(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)

    with pytest.raises(CarouselNotFound):
        upload_references("does-not-exist", [("a.png", b"x")], repo=repo, media_storage=media_storage)
