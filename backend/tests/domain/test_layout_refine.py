import pytest

from app.domain.carousel import PaletteColor, Slide
from app.domain.image_metrics import ImageMetrics
from app.domain.layout_defaults import MARGIN_X, MARGIN_Y
from app.domain.layout_refine import (
    CANVAS_H,
    TextPlacement,
    contrast_ratio,
    estimate_text_height_pct,
    fallback_placements,
    pick_readable_color,
    validate_placements,
)

PALETTE = [
    PaletteColor(hex="#111111", role="background"),
    PaletteColor(hex="#ffffff", role="text"),
    PaletteColor(hex="#f5d90a", role="accent"),
]


def _metrics(density: int = 0, luminance: int = 128) -> ImageMetrics:
    return ImageMetrics(
        cols=12,
        rows=15,
        edge_density=[[density] * 12 for _ in range(15)],
        luminance=[[luminance] * 12 for _ in range(15)],
        avg_color=[[[luminance] * 3 for _ in range(12)] for _ in range(15)],
    )


def _slide(headline="Título de teste", body="corpo de apoio", role="hook", index=1):
    return Slide(index=index, role=role, headline=headline, body=body, visual_prompt="v")


# --- estimate_text_height_pct ------------------------------------------------


def test_short_text_is_a_single_line():
    h = estimate_text_height_pct("Oi", font_size=60, w_pct=80, line_height=1.04)
    assert h == pytest.approx(60 * 1.04 / CANVAS_H * 100)


def test_long_text_wraps_into_more_lines():
    one = estimate_text_height_pct("Oi", 60, 80, 1.04)
    many = estimate_text_height_pct(
        "Uma frase bem mais longa que certamente quebra em várias linhas no canvas",
        60,
        80,
        1.04,
    )
    assert many >= one * 2


def test_explicit_newlines_count_as_lines():
    h1 = estimate_text_height_pct("a", 30, 80, 1.3)
    h3 = estimate_text_height_pct("a\nb\nc", 30, 80, 1.3)
    assert h3 == pytest.approx(h1 * 3)


def test_empty_text_has_zero_height():
    assert estimate_text_height_pct("   ", 60, 80, 1.04) == 0.0


# --- validate_placements: clamps ---------------------------------------------


def test_out_of_bounds_placement_is_clamped_to_margins():
    p = TextPlacement(target="h1", x=-20, y=150, w=200, font_size=64, color="#ffffff")

    validate_placements([p], _slide(), _metrics(), PALETTE)

    assert p.x >= MARGIN_X
    assert p.w <= 100 - 2 * MARGIN_X
    assert p.x + p.w <= 100 - MARGIN_X + 1e-6
    assert p.y + p.h <= 100 - MARGIN_Y + 1e-6


def test_font_sizes_are_clamped_per_target():
    h1 = TextPlacement(target="h1", x=10, y=10, w=80, font_size=20, color="#ffffff")
    body = TextPlacement(target="body", x=10, y=60, w=70, font_size=90, color="#ffffff")

    validate_placements([h1, body], _slide(), _metrics(), PALETTE)

    assert h1.font_size == 56  # "o h1 precisa ser bem grande"
    assert body.font_size == 40


def test_height_is_recomputed_from_content():
    p = TextPlacement(target="h1", x=10, y=10, w=80, h=0, font_size=64, color="#ffffff")

    validate_placements([p], _slide(headline="Oi"), _metrics(), PALETTE)

    assert p.h == pytest.approx(64 * 1.04 / CANVAS_H * 100)


# --- validate_placements: overlap ---------------------------------------------


def test_overlapping_body_is_pushed_below_h1():
    h1 = TextPlacement(target="h1", x=10, y=20, w=80, font_size=64, color="#ffffff")
    body = TextPlacement(target="body", x=10, y=21, w=70, font_size=32, color="#ffffff")

    validate_placements([h1, body], _slide(), _metrics(), PALETTE)

    assert body.y >= h1.y + h1.h
    assert body.y + body.h <= 100 - MARGIN_Y + 1e-6


def test_body_moves_above_h1_when_no_room_below():
    h1 = TextPlacement(target="h1", x=10, y=85, w=80, font_size=64, color="#ffffff")
    body = TextPlacement(target="body", x=10, y=86, w=70, font_size=32, color="#ffffff")

    validate_placements([h1, body], _slide(), _metrics(), PALETTE)

    # h1 got clamped near the bottom; body must not overlap it anymore.
    assert body.y + body.h <= h1.y or body.y >= h1.y + h1.h


def test_text_is_nudged_off_the_progress_chrome():
    # Slide 3 has the progress indicator at the top-right.
    p = TextPlacement(
        target="h1", x=70, y=MARGIN_Y, w=21, font_size=56, color="#ffffff"
    )

    validate_placements([p], _slide(index=3, role="value"), _metrics(), PALETTE)

    assert p.y >= MARGIN_Y + 5.0  # below the progress zone


# --- contrast ------------------------------------------------------------------


def test_contrast_ratio_black_on_white():
    assert contrast_ratio("#000000", 255) == pytest.approx(21.0, abs=0.1)
    assert contrast_ratio("#ffffff", 255) == pytest.approx(1.0, abs=0.01)


def test_pick_readable_color_keeps_passing_proposal():
    assert pick_readable_color("#ffffff", PALETTE, 10, 4.5) == "#ffffff"


def test_pick_readable_color_swaps_unreadable_proposal():
    # White text on a bright region: swap for the palette color with the
    # highest contrast (the near-black background color).
    assert pick_readable_color("#ffffff", PALETTE, 250, 4.5) == "#111111"


def test_validate_swaps_low_contrast_color_using_local_luminance():
    p = TextPlacement(target="body", x=10, y=10, w=70, font_size=32, color="#ffffff")

    validate_placements([p], _slide(), _metrics(luminance=250), PALETTE)

    assert p.color == "#111111"


# --- fallback -------------------------------------------------------------------


def test_fallback_places_h1_and_body_without_overlap():
    slide = _slide()
    placements = fallback_placements(slide, _metrics(), "#ffffff")

    targets = {p.target for p in placements}
    assert targets == {"h1", "body"}
    h1 = next(p for p in placements if p.target == "h1")
    body = next(p for p in placements if p.target == "body")
    assert h1.font_size == 76  # hook keeps the big default
    assert body.y >= h1.y + h1.h
    assert h1.x >= MARGIN_X and body.x >= MARGIN_X


def test_fallback_skips_body_when_slide_has_none():
    placements = fallback_placements(_slide(body=""), _metrics(), "#ffffff")
    assert [p.target for p in placements] == ["h1"]


def test_fallback_prefers_lower_band_on_cta():
    placements = fallback_placements(_slide(role="cta", index=5), _metrics(), "#ffffff")
    h1 = next(p for p in placements if p.target == "h1")
    assert h1.y >= 55
