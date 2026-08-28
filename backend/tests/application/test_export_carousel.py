import pytest

from app.adapters.storage.local_media_storage import LocalMediaStorage
from app.application.use_cases.create_carousel import create_carousel
from app.application.use_cases.export_carousel import export_carousel, slide_export_ext
from app.domain.carousel import SlideElement
from app.domain.errors import GenerationInProgress, NoPlanYet

from tests.application.test_plan_carousel import _make_plan
from tests.fakes import FakeCarouselRepository, FakeVideoRenderer, SyncJobRunner


def _seed(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)
    state.plan = _make_plan(None)
    repo.save(state)
    return repo, media_storage, job_runner, state


def test_static_slide_exports_composited_png(tmp_path):
    repo, media_storage, job_runner, state = _seed(tmp_path)
    renderer = FakeVideoRenderer()

    result = export_carousel(
        state.id,
        repo=repo,
        media_storage=media_storage,
        video_renderer=renderer,
        job_runner=job_runner,
        media_origin="",
    )

    assert result.plan.slides[0].export_status == "done"
    assert len(renderer.still_calls) == 1
    assert renderer.calls == []
    out = media_storage.export_output_path(state.id, 1, "png")
    assert out.exists()


def test_slide_with_video_block_exports_mp4(tmp_path):
    repo, media_storage, job_runner, state = _seed(tmp_path)
    state = repo.load(state.id)
    state.plan.slides[0].elements.append(
        SlideElement(
            id="s1-vid",
            type="video",
            role="visual",
            media_url="/media/x/media/clip.mp4",
            media_duration_seconds=7.5,
        )
    )
    repo.save(state)
    renderer = FakeVideoRenderer()

    result = export_carousel(
        state.id,
        repo=repo,
        media_storage=media_storage,
        video_renderer=renderer,
        job_runner=job_runner,
        media_origin="http://origin",
    )

    assert result.plan.slides[0].export_status == "done"
    assert len(renderer.calls) == 1
    props, out_path = renderer.calls[0]
    assert out_path == media_storage.export_output_path(state.id, 1, "mp4")
    # media_url must be origin-prefixed so headless Chromium can fetch it.
    video_el = next(e for e in props["elements"] if e["type"] == "video")
    assert video_el["media_url"] == "http://origin/media/x/media/clip.mp4"


def test_animated_slide_exports_mp4(tmp_path):
    repo, media_storage, job_runner, state = _seed(tmp_path)
    state = repo.load(state.id)
    state.plan.slides[0].motion.animate = True
    repo.save(state)
    renderer = FakeVideoRenderer()

    export_carousel(
        state.id,
        repo=repo,
        media_storage=media_storage,
        video_renderer=renderer,
        job_runner=job_runner,
        media_origin="",
    )

    assert len(renderer.calls) == 1
    assert renderer.still_calls == []


def test_export_replaces_stale_export_in_other_format(tmp_path):
    repo, media_storage, job_runner, state = _seed(tmp_path)
    stale = media_storage.export_output_path(state.id, 1, "mp4")
    stale.write_bytes(b"old-mp4")
    renderer = FakeVideoRenderer()

    export_carousel(
        state.id,
        repo=repo,
        media_storage=media_storage,
        video_renderer=renderer,
        job_runner=job_runner,
        media_origin="",
    )

    assert not stale.exists()
    assert media_storage.export_output_path(state.id, 1, "png").exists()


def test_export_marks_error_on_render_failure(tmp_path):
    repo, media_storage, job_runner, state = _seed(tmp_path)

    class BoomRenderer(FakeVideoRenderer):
        def render_still(self, props, output_path):
            raise RuntimeError("chromium exploded")

    result = export_carousel(
        state.id,
        repo=repo,
        media_storage=media_storage,
        video_renderer=BoomRenderer(),
        job_runner=job_runner,
        media_origin="",
    )

    slide = result.plan.slides[0]
    assert slide.export_status == "error"
    assert "chromium exploded" in slide.export_error
    assert result.status == "error"


def test_export_raises_without_plan(tmp_path):
    repo = FakeCarouselRepository()
    state = create_carousel(repo=repo)

    with pytest.raises(NoPlanYet):
        export_carousel(
            state.id,
            repo=repo,
            media_storage=LocalMediaStorage(tmp_path),
            video_renderer=FakeVideoRenderer(),
            job_runner=SyncJobRunner(),
            media_origin="",
        )


def test_export_raises_when_job_active(tmp_path):
    repo, media_storage, job_runner, state = _seed(tmp_path)
    job_runner._active.add(state.id)

    with pytest.raises(GenerationInProgress):
        export_carousel(
            state.id,
            repo=repo,
            media_storage=media_storage,
            video_renderer=FakeVideoRenderer(),
            job_runner=job_runner,
            media_origin="",
        )


def test_slide_export_ext_helper(tmp_path):
    plan = _make_plan(None)
    slide = plan.slides[0]
    assert slide_export_ext(slide) == "png"

    slide.motion.animate = True
    assert slide_export_ext(slide) == "mp4"

    slide.motion.animate = False
    slide.elements.append(
        SlideElement(id="v", type="video", role="visual", media_url="/media/v.mp4")
    )
    assert slide_export_ext(slide) == "mp4"
