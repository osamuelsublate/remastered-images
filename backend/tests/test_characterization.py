"""Characterization tests pinning the observable API behavior (status codes,
state transitions). Talks to the real FastAPI app via TestClient; only the
AI-provider ports are faked, via ``app.dependency_overrides`` — the same
mechanism production code uses to swap adapters.
"""

from __future__ import annotations

import time

from app.api import deps
from app.domain.carousel import ArtDirection, CarouselPlan, PaletteColor, Slide, SlideMotion
from app.main import app

from tests.fakes import FakeImageAIProvider, FakeTextAIProvider


def _motion() -> SlideMotion:
    return SlideMotion(
        animate=False,
        mode="image",
        preset="none",
        intensity="subtle",
        duration_seconds=4.0,
        note="",
    )


def _art_direction() -> ArtDirection:
    return ArtDirection(
        palette=[PaletteColor(hex="#000000", role="background")],
        typography="grotesca pesada condensada",
        icon_style="line icons",
        layout="grid simples, margens generosas",
        logo_policy="sem logos externos",
        mood="minimal",
        motion="sutil",
    )


def _carousel_plan(n: int = 2) -> CarouselPlan:
    slides = [
        Slide(
            index=i + 1,
            role="hook" if i == 0 else "cta",
            headline=f"Headline {i}",
            body="",
            visual_prompt="a simple line icon",
            swipe_cue="",
            motion=_motion(),
        )
        for i in range(n)
    ]
    return CarouselPlan(
        title="Carrossel de teste",
        handle="@teste",
        art_direction=_art_direction(),
        caption="Legenda de teste",
        hashtags=["teste", "carrossel"],
        slides=slides,
    )


def _override_ai(plan_factory, *, image_delay: float = 0.0) -> None:
    app.dependency_overrides[deps.get_text_ai_provider] = lambda: FakeTextAIProvider(plan_factory)
    app.dependency_overrides[deps.get_image_ai_provider] = lambda: FakeImageAIProvider(
        delay=image_delay
    )


def _clear_ai_overrides() -> None:
    app.dependency_overrides.pop(deps.get_text_ai_provider, None)
    app.dependency_overrides.pop(deps.get_image_ai_provider, None)


def _wait_until_not_generating(client, cid, timeout=5.0):
    deadline = time.time() + timeout
    state = None
    while time.time() < deadline:
        state = client.get(f"/api/carousels/{cid}").json()
        if state["status"] not in ("generating", "rendering"):
            return state
        time.sleep(0.05)
    return state


def test_create_carousel_returns_draft_with_greeting(client):
    res = client.post("/api/carousels")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "draft"
    assert body["id"]
    assert len(body["messages"]) == 1
    assert body["messages"][0]["role"] == "assistant"


def test_get_missing_carousel_returns_404(client):
    res = client.get("/api/carousels/does-not-exist")
    assert res.status_code == 404


def test_plan_then_generate_reaches_done(client):
    _override_ai(lambda brief: _carousel_plan(2))
    try:
        cid = client.post("/api/carousels").json()["id"]

        planned = client.post(f"/api/carousels/{cid}/plan", json={"brief": {"topic": "teste"}})
        assert planned.status_code == 200
        plan = planned.json()["plan"]
        assert len(plan["slides"]) == 2
        assert planned.json()["status"] == "planned"

        generated = client.post(
            f"/api/carousels/{cid}/generate", json={"plan": plan, "quality": "low"}
        )
        assert generated.status_code == 200
        assert generated.json()["status"] == "generating"

        final = _wait_until_not_generating(client, cid)
        assert final["status"] == "done"
        assert all(s["status"] == "done" for s in final["plan"]["slides"])
        assert all(s["image_url"] for s in final["plan"]["slides"])
    finally:
        _clear_ai_overrides()


def test_generate_while_active_returns_409(client):
    _override_ai(lambda brief: _carousel_plan(1), image_delay=0.5)
    try:
        cid = client.post("/api/carousels").json()["id"]
        plan = client.post(
            f"/api/carousels/{cid}/plan", json={"brief": {"topic": "teste"}}
        ).json()["plan"]

        first = client.post(
            f"/api/carousels/{cid}/generate", json={"plan": plan, "quality": "low"}
        )
        assert first.status_code == 200

        second = client.post(
            f"/api/carousels/{cid}/generate", json={"plan": plan, "quality": "low"}
        )
        assert second.status_code == 409

        _wait_until_not_generating(client, cid)  # drain the background job
    finally:
        _clear_ai_overrides()


def test_regenerate_without_plan_returns_400(client):
    cid = client.post("/api/carousels").json()["id"]
    res = client.post(f"/api/carousels/{cid}/regenerate", json={"indices": [1], "instruction": ""})
    assert res.status_code == 400


def test_animate_without_plan_returns_400(client):
    cid = client.post("/api/carousels").json()["id"]
    res = client.post(f"/api/carousels/{cid}/animate", json={"indices": []})
    assert res.status_code == 400


def test_download_without_slides_returns_404(client):
    cid = client.post("/api/carousels").json()["id"]
    res = client.get(f"/api/carousels/{cid}/download")
    assert res.status_code == 404


def test_update_slide_layout_persists_and_is_returned_by_get(client):
    _override_ai(lambda brief: _carousel_plan(2))
    try:
        cid = client.post("/api/carousels").json()["id"]
        plan = client.post(
            f"/api/carousels/{cid}/plan", json={"brief": {"topic": "teste"}}
        ).json()["plan"]

        res = client.patch(
            f"/api/carousels/{cid}/slides/1/layout",
            json={"background_rect": {"x": 5, "y": 6, "w": 40, "h": 50}},
        )
        assert res.status_code == 200
        assert res.json()["plan"]["slides"][0]["background_rect"] == {
            "x": 5, "y": 6, "w": 40, "h": 50,
        }

        refetched = client.get(f"/api/carousels/{cid}")
        assert refetched.json()["plan"]["slides"][0]["background_rect"]["x"] == 5
        assert plan  # keep the planned copy referenced for clarity
    finally:
        _clear_ai_overrides()


def test_update_slide_layout_without_plan_returns_400(client):
    cid = client.post("/api/carousels").json()["id"]
    res = client.patch(
        f"/api/carousels/{cid}/slides/1/layout",
        json={"background_rect": {"x": 0, "y": 0, "w": 100, "h": 100}},
    )
    assert res.status_code == 400


def test_replace_slide_image_uploads_and_updates_slide(client):
    _override_ai(lambda brief: _carousel_plan(1))
    try:
        cid = client.post("/api/carousels").json()["id"]
        client.post(f"/api/carousels/{cid}/plan", json={"brief": {"topic": "teste"}})

        res = client.post(
            f"/api/carousels/{cid}/slides/1/image",
            files={"file": ("upload.png", b"fake-png-bytes", "image/png")},
        )
        assert res.status_code == 200
        slide = res.json()["plan"]["slides"][0]
        assert slide["status"] == "done"
        assert slide["image_url"]
    finally:
        _clear_ai_overrides()
