from app.domain.carousel import PaletteColor, Slide, SlideElement
from app.domain.layout_defaults import default_elements_for_slide, patch_slide_elements_content


def _slide(**overrides) -> Slide:
    base = dict(index=1, role="hook", headline="H", body="", visual_prompt="v", swipe_cue="")
    base.update(overrides)
    return Slide(**base)


def test_default_elements_always_include_h1_headline():
    els = default_elements_for_slide(_slide(), plan_handle="", total=5)
    roles = [e.role for e in els]
    assert "h1" in roles
    headline = next(e for e in els if e.role == "h1")
    assert headline.content == "H"
    assert headline.type == "text"


def test_legacy_headline_role_is_migrated_to_h1():
    el = SlideElement.model_validate(
        {"id": "s1-headline", "type": "text", "role": "headline", "content": "H"}
    )
    assert el.role == "h1"


def test_legacy_h2_h3_body_caption_roles_are_migrated_to_text():
    for legacy_role in ("h2", "h3", "body", "caption"):
        el = SlideElement.model_validate(
            {"id": "s1-blk1", "type": "text", "role": legacy_role, "content": "x"}
        )
        assert el.role == "text"


def test_default_elements_apply_art_direction_fonts():
    els = default_elements_for_slide(
        _slide(body="B"),
        plan_handle="",
        total=5,
        heading_font="Space Grotesk",
        body_font="Lora",
    )
    h1 = next(e for e in els if e.role == "h1")
    body = next(e for e in els if e.id == "s1-body")
    assert h1.style.font_family == "Space Grotesk"
    assert body.style.font_family == "Lora"


def test_default_elements_body_only_when_present():
    with_body = default_elements_for_slide(_slide(body="B"), plan_handle="", total=5)
    assert any(e.id == "s1-body" for e in with_body)

    without_body = default_elements_for_slide(_slide(body=""), plan_handle="", total=5)
    assert not any(e.id == "s1-body" for e in without_body)


def test_swipe_cue_only_on_first_slide():
    first = default_elements_for_slide(
        _slide(index=1, swipe_cue="mais →"), plan_handle="", total=5
    )
    assert any(e.role == "swipe_cue" for e in first)

    later = default_elements_for_slide(
        _slide(index=2, swipe_cue="mais →"), plan_handle="", total=5
    )
    assert not any(e.role == "swipe_cue" for e in later)


def test_handle_only_on_cta_slide_when_present():
    cta_with_handle = default_elements_for_slide(
        _slide(index=5, role="cta"), plan_handle="@marca", total=5
    )
    assert any(e.role == "handle" for e in cta_with_handle)

    cta_without_handle = default_elements_for_slide(
        _slide(index=5, role="cta"), plan_handle="", total=5
    )
    assert not any(e.role == "handle" for e in cta_without_handle)

    value_with_handle = default_elements_for_slide(
        _slide(index=3, role="value"), plan_handle="@marca", total=5
    )
    assert not any(e.role == "handle" for e in value_with_handle)


def test_progress_only_from_second_slide_onward():
    first = default_elements_for_slide(_slide(index=1), plan_handle="", total=5)
    assert not any(e.role == "progress" for e in first)

    second = default_elements_for_slide(_slide(index=2), plan_handle="", total=5)
    progress = next(e for e in second if e.role == "progress")
    assert progress.content == "2/5"


def test_default_elements_pick_palette_colors():
    palette = [
        PaletteColor(hex="#111111", role="background"),
        PaletteColor(hex="#ff0000", role="accent"),
        PaletteColor(hex="#eeeeee", role="text"),
    ]
    second = default_elements_for_slide(_slide(index=2), plan_handle="", total=5, palette=palette)
    headline = next(e for e in second if e.role == "h1")
    progress = next(e for e in second if e.role == "progress")
    assert headline.style.color == "#eeeeee"
    assert progress.style.color == "#ff0000"


def test_patch_preserves_user_customized_rect_and_style():
    slide = _slide(index=2, headline="Original", body="Body original")
    slide.elements = default_elements_for_slide(slide, plan_handle="", total=5)

    # Simulate the user manually dragging/resizing + restyling the headline.
    headline = next(e for e in slide.elements if e.role == "h1")
    headline.rect.x = 42.0
    headline.style.color = "#123456"

    slide.headline = "Revisada pela IA"
    slide.body = "Body revisado"
    patch_slide_elements_content(slide, plan_handle="", total=5)

    patched_headline = next(e for e in slide.elements if e.role == "h1")
    assert patched_headline.content == "Revisada pela IA"
    assert patched_headline.rect.x == 42.0
    assert patched_headline.style.color == "#123456"

    patched_body = next(e for e in slide.elements if e.id == "s2-body")
    assert patched_body.content == "Body revisado"


def test_patch_removes_element_when_content_cleared():
    slide = _slide(index=2, headline="H", body="B")
    slide.elements = default_elements_for_slide(slide, plan_handle="", total=5)
    assert any(e.id == "s2-body" for e in slide.elements)

    slide.body = ""
    patch_slide_elements_content(slide, plan_handle="", total=5)

    assert not any(e.id == "s2-body" for e in slide.elements)


def test_patch_recreates_element_user_deleted_when_ai_brings_content_back():
    slide = _slide(index=2, headline="H", body="")
    slide.elements = default_elements_for_slide(slide, plan_handle="", total=5)
    assert not any(e.id == "s2-body" for e in slide.elements)

    slide.body = "Novo body da IA"
    patch_slide_elements_content(slide, plan_handle="", total=5)

    body = next(e for e in slide.elements if e.id == "s2-body")
    assert body.content == "Novo body da IA"


def test_patch_syncs_by_id_not_confused_by_extra_text_block_same_role():
    """Regression test: an extra user/AI-added block with role="text" must
    not be mistaken for the automatic body block during sync, now that both
    share the same role (the old code matched "by role", which collided)."""
    slide = _slide(index=2, headline="H", body="Body original")
    slide.elements = default_elements_for_slide(slide, plan_handle="", total=5)

    extra = SlideElement(
        id="s2-blk1",
        type="text",
        role="text",
        content="Bloco extra que não deve ser tocado",
    )
    slide.elements.append(extra)

    slide.body = "Body revisado pela IA"
    patch_slide_elements_content(slide, plan_handle="", total=5)

    patched_body = next(e for e in slide.elements if e.id == "s2-body")
    assert patched_body.content == "Body revisado pela IA"

    untouched_extra = next(e for e in slide.elements if e.id == "s2-blk1")
    assert untouched_extra.content == "Bloco extra que não deve ser tocado"
