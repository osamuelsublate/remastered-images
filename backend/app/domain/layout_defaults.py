"""Default per-role layout: turns plain copy into positioned ``SlideElement``s.

Mirrors the same conditional chrome rules ``SlideMotion.tsx`` used to bake in
unconditionally (handle only on the CTA slide, progress only from the 2nd
slide onward, swipe cue only on the cover) — just expressed as concrete,
independently editable elements instead of always-on render logic. Rects are
percentages (0-100) of the 1080x1350 canvas so they're resolution-independent.
"""

from __future__ import annotations

from .carousel import ArtDirection, ElementRect, PaletteColor, Slide, SlideElement, TextStyle
from .fonts import DEFAULT_FONT, normalize_font

# Same visual margin Remotion's ``Chrome``/text blocks use (96px), expressed
# as a percentage of each axis of the 1080x1350 canvas.
MARGIN_X = 8.9
MARGIN_Y = 7.1

# (x, y, w, h) in percent, headline/body area per role — before the margin is
# subtracted from x/w. Purely a sane starting point; users tune it visually.
_ROLE_LAYOUT: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "hook": {"headline": (0, 8, 100, 42), "body": (0, 54, 82, 16)},
    "context": {"headline": (0, 8, 100, 22), "body": (0, 32, 88, 20)},
    "value": {"headline": (0, 8, 100, 18), "body": (0, 28, 88, 18)},
    "proof": {"headline": (0, 8, 100, 18), "body": (0, 28, 88, 18)},
    "cta": {"headline": (0, 58, 100, 22), "body": (0, 82, 88, 10)},
}


def _color_for(palette: list[PaletteColor] | None, role: str, fallback: str) -> str:
    if palette:
        for c in palette:
            if role in c.role.lower():
                return c.hex
    return fallback


def fonts_for(art: ArtDirection | None) -> tuple[str, str]:
    """(heading_font, body_font) from the plan's art direction, normalized to
    the curated library."""
    if art is None:
        return DEFAULT_FONT, DEFAULT_FONT
    heading = normalize_font(art.font_family)
    body = normalize_font(art.font_family_secondary)
    return heading, body


def default_elements_for_slide(
    slide: Slide,
    plan_handle: str,
    total: int,
    palette: list[PaletteColor] | None = None,
    *,
    heading_font: str = DEFAULT_FONT,
    body_font: str = DEFAULT_FONT,
) -> list[SlideElement]:
    """Default overlay layout for a freshly (re)planned slide.

    Only produces elements that make sense for this specific slide (e.g. no
    ``progress`` on slide 1, no ``handle`` outside the CTA slide) — same
    conditions the old hardcoded ``Chrome`` component used.
    """
    text = _color_for(palette, "text", "#ffffff")
    accent = _color_for(palette, "accent", "#ff6b1a")
    layout = _ROLE_LAYOUT.get(slide.role, _ROLE_LAYOUT["value"])
    elements: list[SlideElement] = []

    hx, hy, hw, hh = layout["headline"]
    elements.append(
        SlideElement(
            id=f"s{slide.index}-h1",
            type="text",
            role="h1",
            rect=ElementRect(x=hx + MARGIN_X, y=hy, w=hw - 2 * MARGIN_X, h=hh),
            z_index=10,
            content=slide.headline,
            style=TextStyle(
                font_size=76 if slide.role == "hook" else 52,
                color=text,
                weight=800,
                align="left",
                font_family=heading_font,
            ),
        )
    )

    if slide.body.strip():
        bx, by, bw, bh = layout["body"]
        elements.append(
            SlideElement(
                id=f"s{slide.index}-body",
                type="text",
                role="text",
                rect=ElementRect(x=bx + MARGIN_X, y=by, w=bw - MARGIN_X, h=bh),
                z_index=9,
                content=slide.body,
                style=TextStyle(
                    font_size=34, color=text, weight=500, align="left", font_family=body_font
                ),
            )
        )

    if slide.swipe_cue.strip() and slide.index <= 1:
        elements.append(
            SlideElement(
                id=f"s{slide.index}-swipe_cue",
                type="text",
                role="swipe_cue",
                rect=ElementRect(
                    x=100 - MARGIN_X - 32, y=100 - MARGIN_Y - 6, w=32, h=6
                ),
                z_index=8,
                content=slide.swipe_cue,
                style=TextStyle(
                    font_size=28, color=accent, weight=600, align="right", font_family=body_font
                ),
            )
        )

    if slide.role == "cta" and plan_handle.strip():
        elements.append(
            SlideElement(
                id=f"s{slide.index}-handle",
                type="text",
                role="handle",
                rect=ElementRect(x=MARGIN_X, y=100 - MARGIN_Y - 5, w=50, h=5),
                z_index=8,
                content=plan_handle,
                style=TextStyle(
                    font_size=30, color=text, weight=600, align="left", font_family=body_font
                ),
            )
        )

    if slide.index > 1:
        elements.append(
            SlideElement(
                id=f"s{slide.index}-progress",
                type="text",
                role="progress",
                rect=ElementRect(x=100 - MARGIN_X - 22, y=MARGIN_Y, w=22, h=5),
                z_index=8,
                content=f"{slide.index}/{total}",
                style=TextStyle(
                    font_size=28, color=accent, weight=700, align="right", font_family=body_font
                ),
            )
        )

    return elements


def _default_by_id(
    slide: Slide,
    id_key: str,
    plan_handle: str,
    total: int,
    palette: list[PaletteColor] | None,
    heading_font: str,
    body_font: str,
) -> SlideElement | None:
    for el in default_elements_for_slide(
        slide, plan_handle, total, palette, heading_font=heading_font, body_font=body_font
    ):
        if el.id == id_key:
            return el
    return None


def patch_slide_elements_content(
    slide: Slide,
    *,
    plan_handle: str,
    total: int,
    palette: list[PaletteColor] | None = None,
    heading_font: str = DEFAULT_FONT,
    body_font: str = DEFAULT_FONT,
) -> None:
    """Sync ``slide.elements`` after an AI revision changed
    ``headline``/``body``/``swipe_cue``, WITHOUT touching the ``rect``/``style``
    the user may already have customized in the editor.

    Matches by the deterministic id of each auto-managed block
    (``s{index}-h1``/``s{index}-body``/``s{index}-swipe_cue``) rather than by
    ``role``: now that extra user/AI-added blocks can also carry ``role="text"``,
    matching by role would risk syncing the wrong element whenever a slide has
    more than one text block. ``role`` stays a pure style label.

    - An existing element for that id just gets its ``content`` refreshed.
    - An id that becomes non-empty but has no element yet gets one created
      from the default layout (covers "user deleted it, AI brought it back").
    - An id that becomes empty has its element removed.
    """
    by_id = {el.id: el for el in slide.elements}

    def _sync(id_key: str, content: str) -> None:
        existing = by_id.get(id_key)
        if content.strip():
            if existing is not None:
                existing.content = content
            else:
                fresh = _default_by_id(
                    slide, id_key, plan_handle, total, palette, heading_font, body_font
                )
                if fresh is not None:
                    fresh.content = content
                    slide.elements.append(fresh)
        elif existing is not None:
            slide.elements.remove(existing)

    _sync(f"s{slide.index}-h1", slide.headline)
    _sync(f"s{slide.index}-body", slide.body)
    _sync(f"s{slide.index}-swipe_cue", slide.swipe_cue if slide.index <= 1 else "")
