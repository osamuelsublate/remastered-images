import pytest

from app.application.use_cases.create_carousel import create_carousel
from app.application.use_cases.update_slide_layout import update_slide_layout
from app.domain.carousel import ElementRect
from app.domain.errors import CarouselNotFound, InvalidSlideSelection, NoPlanYet

from tests.application.test_plan_carousel import _make_plan
from tests.fakes import FakeCarouselRepository


def _seed_planned_carousel():
    repo = FakeCarouselRepository()
    state = create_carousel(repo=repo)
    state.plan = _make_plan(None)
    repo.save(state)
    return repo, state.id


def test_update_slide_layout_applies_background_rect_and_elements():
    repo, cid = _seed_planned_carousel()
    new_rect = ElementRect(x=10, y=20, w=60, h=70)
    new_elements = list(repo.load(cid).plan.slides[0].elements)

    result = update_slide_layout(
        cid, 1, background_rect=new_rect, elements=new_elements, repo=repo
    )

    assert result.plan.slides[0].background_rect == new_rect
    assert result.plan.slides[0].elements == new_elements


def test_update_slide_layout_partial_patch_only_touches_provided_fields():
    repo, cid = _seed_planned_carousel()
    original_elements = repo.load(cid).plan.slides[0].elements
    new_rect = ElementRect(x=1, y=2, w=3, h=4)

    result = update_slide_layout(cid, 1, background_rect=new_rect, elements=None, repo=repo)

    assert result.plan.slides[0].background_rect == new_rect
    assert result.plan.slides[0].elements == original_elements


def test_update_slide_layout_raises_when_carousel_missing():
    repo = FakeCarouselRepository()
    with pytest.raises(CarouselNotFound):
        update_slide_layout(
            "does-not-exist", 1, background_rect=None, elements=None, repo=repo
        )


def test_update_slide_layout_raises_without_plan():
    repo = FakeCarouselRepository()
    state = create_carousel(repo=repo)
    with pytest.raises(NoPlanYet):
        update_slide_layout(state.id, 1, background_rect=None, elements=None, repo=repo)


def test_update_slide_layout_raises_on_invalid_index():
    repo, cid = _seed_planned_carousel()
    with pytest.raises(InvalidSlideSelection):
        update_slide_layout(cid, 99, background_rect=None, elements=None, repo=repo)
