import pytest
from PIL import Image

from app.adapters.storage.local_media_storage import LocalMediaStorage
from app.application.use_cases.create_carousel import create_carousel
from app.application.use_cases.generate_images import generate_images
from app.domain.errors import GenerationInProgress

from tests.application.test_plan_carousel import _make_plan
from tests.fakes import (
    FakeCarouselRepository,
    FakeImageAIProvider,
    FakeTextAIProvider,
    SyncJobRunner,
)


class _RealPngImageAI(FakeImageAIProvider):
    """Writes an actual decodable PNG so the layout-refine step can run."""

    def generate_slide_image(self, *, prompt, output_path, references=None, quality=None):
        self.calls.append(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (108, 135), (40, 40, 40)).save(output_path)


def test_generate_images_happy_path(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    image_ai = FakeImageAIProvider()
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)
    plan = _make_plan(None)

    result = generate_images(
        state.id,
        plan,
        "low",
        repo=repo,
        media_storage=media_storage,
        image_ai=image_ai,
        job_runner=job_runner,
    )

    assert result.status == "done"
    assert all(s.status == "done" for s in result.plan.slides)
    assert all(s.image_url for s in result.plan.slides)
    assert len(image_ai.calls) == len(plan.slides)


def test_generate_images_refines_layout_when_text_ai_provided(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    image_ai = _RealPngImageAI()
    text_ai = FakeTextAIProvider()  # default fake places the h1 at x=10, y=10
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)
    plan = _make_plan(None)

    result = generate_images(
        state.id,
        plan,
        "low",
        repo=repo,
        media_storage=media_storage,
        image_ai=image_ai,
        job_runner=job_runner,
        text_ai=text_ai,
    )

    assert result.status == "done"
    assert len(text_ai.layout_calls) == 1
    h1 = next(e for e in result.plan.slides[0].elements if e.id == "s1-h1")
    assert (h1.rect.x, h1.rect.y) == (10, 10)
    assert h1.style.font_size == 64


def test_generate_images_survives_layout_refine_failure(tmp_path):
    # The stock fake writes undecodable bytes: image analysis blows up, the
    # refinement is skipped, and generation still completes with the default
    # layout untouched.
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    image_ai = FakeImageAIProvider()
    text_ai = FakeTextAIProvider()
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)
    plan = _make_plan(None)
    default_layout = [e.model_dump() for e in plan.slides[0].elements]

    result = generate_images(
        state.id,
        plan,
        "low",
        repo=repo,
        media_storage=media_storage,
        image_ai=image_ai,
        job_runner=job_runner,
        text_ai=text_ai,
    )

    assert result.status == "done"
    assert text_ai.layout_calls == []
    assert [e.model_dump() for e in result.plan.slides[0].elements] == default_layout


def test_generate_images_raises_when_already_active(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    image_ai = FakeImageAIProvider()
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)
    plan = _make_plan(None)
    job_runner._active.add(state.id)  # simulate an in-flight job

    with pytest.raises(GenerationInProgress):
        generate_images(
            state.id,
            plan,
            "low",
            repo=repo,
            media_storage=media_storage,
            image_ai=image_ai,
            job_runner=job_runner,
        )


def test_generate_images_marks_slide_error_on_provider_failure(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)
    plan = _make_plan(None)

    class _FailingImageAI:
        def generate_slide_image(self, **kwargs):
            raise RuntimeError("boom")

    result = generate_images(
        state.id,
        plan,
        "low",
        repo=repo,
        media_storage=media_storage,
        image_ai=_FailingImageAI(),
        job_runner=job_runner,
    )

    assert result.status == "error"
    assert result.plan.slides[0].status == "error"
    assert result.plan.slides[0].error == "boom"
