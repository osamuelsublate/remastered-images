import pytest

from app.application.use_cases.create_carousel import create_carousel
from app.application.use_cases.plan_carousel import plan_carousel
from app.domain.carousel import Brief
from app.domain.errors import CarouselNotFound, PlanningFailed

from tests.fakes import FakeCarouselRepository, FakeTextAIProvider


def _make_plan(brief: Brief):
    from app.domain.carousel import ArtDirection, CarouselPlan, PaletteColor, Slide, SlideMotion
    from app.domain.layout_defaults import default_elements_for_slide

    motion = SlideMotion(
        animate=False, mode="image", preset="none", intensity="subtle",
        duration_seconds=4.0, note="",
    )
    palette = [PaletteColor(hex="#000", role="background")]
    slide = Slide(index=1, role="hook", headline="H", visual_prompt="v", motion=motion)
    slide.elements = default_elements_for_slide(slide, "", 1, palette)
    return CarouselPlan(
        title="Título",
        handle="",
        art_direction=ArtDirection(
            palette=palette,
            typography="grotesca",
            icon_style="line icons",
            layout="grid",
            logo_policy="sem logos",
            mood="",
            motion="sutil",
        ),
        caption="Legenda",
        hashtags=["a"],
        slides=[slide],
    )


def test_plan_carousel_sets_plan_and_status():
    repo = FakeCarouselRepository()
    text_ai = FakeTextAIProvider(plan_factory=_make_plan)
    state = create_carousel(repo=repo)
    brief = Brief(topic="teste")

    updated = plan_carousel(state.id, brief, repo=repo, text_ai=text_ai)

    assert updated.status == "planned"
    assert updated.brief == brief
    assert updated.plan is not None
    assert len(updated.plan.slides) == 1
    assert text_ai.plan_calls == [brief]


def test_plan_carousel_raises_when_carousel_missing():
    repo = FakeCarouselRepository()
    text_ai = FakeTextAIProvider(plan_factory=_make_plan)

    with pytest.raises(CarouselNotFound):
        plan_carousel("does-not-exist", Brief(topic="teste"), repo=repo, text_ai=text_ai)


def test_plan_carousel_wraps_provider_failure():
    repo = FakeCarouselRepository()

    def _boom(brief):
        raise RuntimeError("provider down")

    text_ai = FakeTextAIProvider(plan_factory=_boom)
    state = create_carousel(repo=repo)

    with pytest.raises(PlanningFailed):
        plan_carousel(state.id, Brief(topic="teste"), repo=repo, text_ai=text_ai)

    # State must be left untouched (still no plan) when planning fails.
    assert repo.load(state.id).plan is None
