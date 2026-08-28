from app.prompts import ROLE_TEMPLATES, build_image_prompt

from tests.application.test_plan_carousel import _make_plan


def test_build_image_prompt_never_includes_the_actual_copy():
    plan = _make_plan(None)
    slide = plan.slides[0]
    slide.headline = "UM HEADLINE MUITO ESPECÍFICO"
    slide.body = "UM BODY MUITO ESPECÍFICO"
    slide.swipe_cue = "SWIPE CUE ESPECÍFICO"

    prompt = build_image_prompt(plan, slide, total=1)

    # The background prompt must be visual-only: none of the actual copy
    # strings should leak into it (that's the whole point of the layered
    # editor — text is a separate layer, not baked into the AI image).
    assert slide.headline not in prompt
    assert slide.body not in prompt
    assert slide.swipe_cue not in prompt
    assert "Render EXACTLY this text" not in prompt
    assert "Progress indicator" not in prompt


def test_build_image_prompt_instructs_no_text_at_all():
    plan = _make_plan(None)
    slide = plan.slides[0]

    prompt = build_image_prompt(plan, slide, total=1)

    assert "NO text" in prompt or "ZERO text" in prompt.upper() or "no text" in prompt.lower()


def test_role_templates_reserve_space_instead_of_drawing_text():
    for role, template in ROLE_TEMPLATES.items():
        assert "NO text" in template, f"role={role} should instruct a text-free background"
