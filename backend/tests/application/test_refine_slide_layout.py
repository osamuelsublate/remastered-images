from PIL import Image

from app.application.use_cases.refine_slide_layout import refine_slide_layout
from app.domain.carousel import ArtDirection, CarouselPlan, PaletteColor, Slide
from app.domain.layout_defaults import MARGIN_X, MARGIN_Y, default_elements_for_slide
from app.domain.layout_refine import TextPlacement

from tests.fakes import FakeTextAIProvider

PALETTE = [
    PaletteColor(hex="#111111", role="background"),
    PaletteColor(hex="#ffffff", role="text"),
    PaletteColor(hex="#f5d90a", role="accent"),
]


def _make_plan() -> CarouselPlan:
    slide = Slide(
        index=1,
        role="hook",
        headline="Título grande",
        body="corpo de apoio do slide",
        visual_prompt="v",
    )
    slide.elements = default_elements_for_slide(slide, "", 1, PALETTE)
    return CarouselPlan(
        title="T",
        handle="",
        art_direction=ArtDirection(
            palette=PALETTE,
            typography="grotesca",
            icon_style="line icons",
            layout="grid",
            logo_policy="sem logos",
            mood="",
            motion="sutil",
        ),
        caption="c",
        hashtags=["a"],
        slides=[slide],
    )


def _write_png(path, color=(40, 40, 40)):
    Image.new("RGB", (216, 270), color).save(path)
    return path


def _element(slide, suffix):
    return next(e for e in slide.elements if e.id == f"s{slide.index}-{suffix}")


def test_vision_placements_are_applied_to_the_auto_elements(tmp_path):
    plan = _make_plan()
    slide = plan.slides[0]
    image = _write_png(tmp_path / "bg.png")
    text_ai = FakeTextAIProvider(
        layout_factory=lambda s: [
            TextPlacement(
                target="h1", x=15, y=55, w=70, align="center", font_size=88, color="#f5d90a"
            ),
            TextPlacement(
                target="body", x=15, y=80, w=60, align="center", font_size=30, color="#ffffff"
            ),
        ]
    )

    refine_slide_layout(slide, image, plan, 1, text_ai=text_ai)

    assert len(text_ai.layout_calls) == 1
    h1 = _element(slide, "h1")
    assert (h1.rect.x, h1.rect.y, h1.rect.w) == (15, 55, 70)
    assert h1.rect.h > 0
    assert h1.style.font_size == 88
    assert h1.style.align == "center"
    assert h1.style.color == "#f5d90a"
    body = _element(slide, "body")
    assert body.rect.x == 15
    assert body.style.font_size == 30
    # Anti-overlap kept the body clear of the h1.
    assert body.rect.y >= h1.rect.y + h1.rect.h or body.rect.y + body.rect.h <= h1.rect.y


def test_vision_coordinates_are_validated_not_trusted(tmp_path):
    plan = _make_plan()
    slide = plan.slides[0]
    image = _write_png(tmp_path / "bg.png")
    text_ai = FakeTextAIProvider(
        layout_factory=lambda s: [
            # Hallucinated coordinates way outside the canvas and a tiny h1.
            TextPlacement(target="h1", x=-50, y=300, w=500, font_size=12, color="#ffffff"),
        ]
    )

    refine_slide_layout(slide, image, plan, 1, text_ai=text_ai)

    h1 = _element(slide, "h1")
    assert h1.rect.x >= MARGIN_X
    assert h1.rect.x + h1.rect.w <= 100 - MARGIN_X + 1e-6
    assert h1.rect.y + h1.rect.h <= 100 - MARGIN_Y + 1e-6
    assert h1.style.font_size == 56  # clamped up to the h1 minimum


def test_deterministic_fallback_when_vision_fails(tmp_path):
    plan = _make_plan()
    slide = plan.slides[0]
    image = _write_png(tmp_path / "bg.png")

    def _boom(_slide):
        raise RuntimeError("vision down")

    text_ai = FakeTextAIProvider(layout_factory=_boom)

    refine_slide_layout(slide, image, plan, 1, text_ai=text_ai)

    # Fallback ran: hook h1 keeps the big default size and lands inside the
    # margins of the calmest band (uniform image -> top-left of the band).
    assert len(text_ai.layout_calls) == 1
    h1 = _element(slide, "h1")
    assert h1.style.font_size == 76
    assert h1.rect.x >= MARGIN_X
    assert h1.rect.y >= MARGIN_Y


def test_fallback_when_vision_returns_no_h1(tmp_path):
    plan = _make_plan()
    slide = plan.slides[0]
    image = _write_png(tmp_path / "bg.png")
    text_ai = FakeTextAIProvider(
        layout_factory=lambda s: [
            TextPlacement(target="body", x=10, y=50, w=60, font_size=30, color="#ffffff")
        ]
    )

    refine_slide_layout(slide, image, plan, 1, text_ai=text_ai)

    h1 = _element(slide, "h1")
    assert h1.style.font_size == 76  # fallback layout, not the useless answer


def test_default_layout_is_kept_when_image_analysis_fails(tmp_path):
    plan = _make_plan()
    slide = plan.slides[0]
    before = [e.model_dump() for e in slide.elements]
    text_ai = FakeTextAIProvider()

    refine_slide_layout(slide, tmp_path / "does-not-exist.png", plan, 1, text_ai=text_ai)

    assert [e.model_dump() for e in slide.elements] == before
    assert text_ai.layout_calls == []  # never even reached the vision call
