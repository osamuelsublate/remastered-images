import pytest

from app.adapters.storage.local_media_storage import LocalMediaStorage
from app.application.use_cases.animate_slides import animate_slides
from app.application.use_cases.create_carousel import create_carousel
from app.domain.errors import GenerationInProgress, InvalidSlideSelection, NoPlanYet

from tests.application.test_plan_carousel import _make_plan
from tests.fakes import FakeCarouselRepository, FakeVideoRenderer, SyncJobRunner


def test_animate_slides_renders_flagged_slides(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)
    plan = _make_plan(None)
    plan.slides[0].motion.animate = True
    plan.slides[0].motion.mode = "vector"
    state.plan = plan
    repo.save(state)

    video_renderer = FakeVideoRenderer()
    result = animate_slides(
        state.id,
        [],
        repo=repo,
        media_storage=media_storage,
        video_renderer=video_renderer,
        job_runner=job_runner,
        media_origin="",
    )

    # Overall `status` reflects slide *image* status (still "pending" here,
    # since no image was ever generated), not motion status — same as the
    # pre-migration ``jobs._finalize`` behavior.
    assert result.status == "planned"
    assert result.plan.slides[0].motion_status == "done"
    assert result.plan.slides[0].video_url
    assert len(video_renderer.calls) == 1


def test_animate_slides_requires_image_for_image_mode(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)
    plan = _make_plan(None)
    plan.slides[0].motion.animate = True
    plan.slides[0].motion.mode = "image"  # no image_url set -> should be rejected
    state.plan = plan
    repo.save(state)

    with pytest.raises(InvalidSlideSelection):
        animate_slides(
            state.id,
            [1],
            repo=repo,
            media_storage=media_storage,
            video_renderer=FakeVideoRenderer(),
            job_runner=job_runner,
            media_origin="",
        )


def test_animate_slides_raises_without_plan():
    repo = FakeCarouselRepository()
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)

    with pytest.raises(NoPlanYet):
        animate_slides(
            state.id,
            [],
            repo=repo,
            media_storage=None,
            video_renderer=FakeVideoRenderer(),
            job_runner=job_runner,
            media_origin="",
        )


def test_animate_slides_raises_when_active(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)
    plan = _make_plan(None)
    plan.slides[0].motion.animate = True
    state.plan = plan
    repo.save(state)
    job_runner._active.add(state.id)

    with pytest.raises(GenerationInProgress):
        animate_slides(
            state.id,
            [],
            repo=repo,
            media_storage=media_storage,
            video_renderer=FakeVideoRenderer(),
            job_runner=job_runner,
            media_origin="",
        )
