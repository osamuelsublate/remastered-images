"""Math-side of content-aware text placement.

The vision agent proposes where h1/body/swipe_cue should sit on the
generated background (``TextPlacement``); this module is the deterministic
safety net that makes those proposals physically valid before they are
applied:

- clamps everything inside the canvas safe margins;
- estimates each block's real height from its content (same shrink-wrap
  behavior the editor applies visually, predicted server-side);
- resolves h1/body overlap and collisions with the fixed chrome
  (progress top-right, handle bottom-left);
- swaps the text color for the best-contrast palette color (WCAG ratio)
  against the measured local luminance when the proposed one would be
  unreadable.

Vision models are good at aesthetics but drift on coordinates — every
number that comes back goes through here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from .carousel import PaletteColor, Slide
from .image_metrics import ImageMetrics
from .layout_defaults import MARGIN_X, MARGIN_Y

CANVAS_W = 1080.0
CANVAS_H = 1350.0

# "o h1 precisa ser bem grande"
H1_FONT_RANGE = (56.0, 110.0)
BODY_FONT_RANGE = (26.0, 40.0)
CUE_FONT_RANGE = (22.0, 34.0)

# Average glyph width as a fraction of font size (roughly right for the
# curated sans/serif faces at the weights we use).
CHAR_WIDTH_FACTOR = 0.55
DEFAULT_LINE_HEIGHT_H1 = 1.04
DEFAULT_LINE_HEIGHT_BODY = 1.3

# Vertical breathing room between stacked text blocks, in canvas %.
BLOCK_GAP = 2.0

# Chrome zones (percent rects) mirroring ``default_elements_for_slide``:
# progress sits top-right from slide 2 on; handle sits bottom-left on the CTA.
_PROGRESS_ZONE = (100 - MARGIN_X - 22, MARGIN_Y, 22.0, 5.0)
_HANDLE_ZONE = (MARGIN_X, 100 - MARGIN_Y - 5, 50.0, 5.0)

PlacementTarget = Literal["h1", "body", "swipe_cue"]


class TextPlacement(BaseModel):
    """One block placement proposed by the vision agent (or the fallback).

    ``h`` starts as whatever the proposer said (often 0) and is replaced by
    the content-based estimate during validation.
    """

    target: PlacementTarget
    x: float
    y: float
    w: float
    h: float = 0.0
    align: Literal["left", "center", "right"] = "left"
    font_size: float
    color: str


def estimate_text_height_pct(
    content: str, font_size: float, w_pct: float, line_height: float
) -> float:
    """Predicted rendered height (canvas %) of a text block: greedy word wrap
    at ~``CHAR_WIDTH_FACTOR * font_size`` px per character."""
    text = content.strip()
    if not text:
        return 0.0
    width_px = max(1.0, w_pct / 100 * CANVAS_W)
    chars_per_line = max(1, int(width_px / (font_size * CHAR_WIDTH_FACTOR)))

    lines = 0
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines += 1
            continue
        current = 0
        lines += 1
        for word in words:
            needed = len(word) if current == 0 else current + 1 + len(word)
            if needed <= chars_per_line:
                current = needed
            else:
                lines += 1
                current = len(word)
    return lines * font_size * line_height / CANVAS_H * 100


def _rects_overlap(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    if len(v) != 6:
        return (255, 255, 255)
    try:
        return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))
    except ValueError:
        return (255, 255, 255)


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def _lin(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(color_hex: str, bg_luminance_255: float) -> float:
    """WCAG contrast ratio between a hex color and a background of the given
    mean luminance (0-255, treated as neutral gray)."""
    gray = round(max(0.0, min(255.0, bg_luminance_255)))
    l_text = _relative_luminance(_hex_to_rgb(color_hex))
    l_bg = _relative_luminance((gray, gray, gray))
    lighter, darker = max(l_text, l_bg), min(l_text, l_bg)
    return (lighter + 0.05) / (darker + 0.05)


def pick_readable_color(
    proposed_hex: str,
    palette: list[PaletteColor],
    bg_luminance_255: float,
    min_ratio: float,
) -> str:
    """Keep the proposed color if it clears ``min_ratio`` against the local
    background; otherwise return the palette color with the highest ratio."""
    if contrast_ratio(proposed_hex, bg_luminance_255) >= min_ratio:
        return proposed_hex
    candidates = [c.hex for c in palette] or [proposed_hex]
    return max(candidates, key=lambda hx: contrast_ratio(hx, bg_luminance_255))


def _clamp_placement(p: TextPlacement) -> None:
    p.w = max(20.0, min(p.w, 100.0 - 2 * MARGIN_X))
    p.x = max(MARGIN_X, min(p.x, 100.0 - MARGIN_X - p.w))
    p.y = max(MARGIN_Y, min(p.y, 100.0 - MARGIN_Y - max(p.h, 4.0)))


def _line_height_for(target: PlacementTarget) -> float:
    return DEFAULT_LINE_HEIGHT_H1 if target == "h1" else DEFAULT_LINE_HEIGHT_BODY


def _font_range_for(target: PlacementTarget) -> tuple[float, float]:
    if target == "h1":
        return H1_FONT_RANGE
    if target == "body":
        return BODY_FONT_RANGE
    return CUE_FONT_RANGE


def _content_for(slide: Slide, target: PlacementTarget) -> str:
    if target == "h1":
        return slide.headline
    if target == "body":
        return slide.body
    return slide.swipe_cue


def validate_placements(
    placements: list[TextPlacement],
    slide: Slide,
    metrics: ImageMetrics,
    palette: list[PaletteColor],
) -> list[TextPlacement]:
    """Normalize the proposed placements in place (and return them):
    font clamping, height estimation, margin clamping, overlap resolution
    and contrast-checked colors."""
    by_target = {p.target: p for p in placements}

    for p in placements:
        lo, hi = _font_range_for(p.target)
        p.font_size = max(lo, min(p.font_size, hi))
        p.h = estimate_text_height_pct(
            _content_for(slide, p.target), p.font_size, p.w, _line_height_for(p.target)
        )
        _clamp_placement(p)

    h1 = by_target.get("h1")
    body = by_target.get("body")
    if h1 is not None and body is not None:
        if _rects_overlap((h1.x, h1.y, h1.w, h1.h), (body.x, body.y, body.w, body.h)):
            below = h1.y + h1.h + BLOCK_GAP
            if below + body.h <= 100.0 - MARGIN_Y:
                body.y = below
            else:
                above = h1.y - BLOCK_GAP - body.h
                body.y = max(MARGIN_Y, above)
            _clamp_placement(body)

    # Keep text off the fixed chrome: progress (top-right, slide >= 2) and
    # handle (bottom-left, CTA slide). A small nudge is enough — these zones
    # are only ~5% tall.
    zones: list[tuple[float, float, float, float]] = []
    if slide.index > 1:
        zones.append(_PROGRESS_ZONE)
    if slide.role == "cta":
        zones.append(_HANDLE_ZONE)
    for p in placements:
        for zx, zy, zw, zh in zones:
            if _rects_overlap((p.x, p.y, p.w, p.h), (zx, zy, zw, zh)):
                if zy < 50:
                    p.y = max(p.y, zy + zh + 1.0)
                else:
                    p.y = min(p.y, zy - p.h - 1.0)
                _clamp_placement(p)

    for p in placements:
        _, bg_lum = metrics.region_stats(p.x, p.y, p.w, max(p.h, 4.0))
        min_ratio = 3.0 if p.target == "h1" else 4.5
        p.color = pick_readable_color(p.color, palette, bg_lum, min_ratio)

    return placements


def fallback_placements(slide: Slide, metrics: ImageMetrics, text_color: str) -> list[TextPlacement]:
    """Deterministic placement when the vision agent is unavailable: put each
    block in the calmest region of the band its role prefers (headline high
    on most slides, low on the CTA — same bias as ``_ROLE_LAYOUT``)."""
    placements: list[TextPlacement] = []
    h1_font = 76.0 if slide.role == "hook" else 60.0
    h1_w = 100.0 - 2 * MARGIN_X
    h1_h = estimate_text_height_pct(slide.headline, h1_font, h1_w, DEFAULT_LINE_HEIGHT_H1)
    h1_band = (55.0, 80.0) if slide.role == "cta" else (MARGIN_Y, 45.0)
    h1_x, h1_y = metrics.best_region(h1_w, max(h1_h, 6.0), y_band=h1_band, x_margin=MARGIN_X)
    placements.append(
        TextPlacement(
            target="h1", x=h1_x, y=h1_y, w=h1_w, h=h1_h,
            font_size=h1_font, color=text_color,
        )
    )

    if slide.body.strip():
        body_font = 32.0
        body_w = 80.0 - MARGIN_X
        body_h = estimate_text_height_pct(
            slide.body, body_font, body_w, DEFAULT_LINE_HEIGHT_BODY
        )
        band_top = h1_y + max(h1_h, 6.0) + BLOCK_GAP
        body_x, body_y = metrics.best_region(
            body_w, max(body_h, 4.0), y_band=(band_top, 92.0), x_margin=MARGIN_X
        )
        placements.append(
            TextPlacement(
                target="body", x=body_x, y=body_y, w=body_w, h=body_h,
                font_size=body_font, color=text_color,
            )
        )
    return placements
