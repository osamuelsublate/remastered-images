import pytest

from app.application.use_cases.create_carousel import create_carousel
from app.application.use_cases.get_carousel import get_carousel
from app.domain.errors import CarouselNotFound

from tests.fakes import FakeCarouselRepository


def test_get_carousel_returns_existing_state():
    repo = FakeCarouselRepository()
    created = create_carousel(repo=repo)

    fetched = get_carousel(created.id, repo=repo)

    assert fetched.id == created.id


def test_get_carousel_raises_when_missing():
    repo = FakeCarouselRepository()

    with pytest.raises(CarouselNotFound):
        get_carousel("does-not-exist", repo=repo)
