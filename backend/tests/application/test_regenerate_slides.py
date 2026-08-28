import pytest

from app.adapters.storage.local_media_storage import LocalMediaStorage
from app.application.use_cases.create_carousel import create_carousel
from app.application.use_cases.generate_images import generate_images
from app.application.use_cases.regenerate_slides import regenerate_slides
from app.domain.carousel import SlideRevision
from app.domain.errors import GenerationInProgress, InvalidSlideSelection, NoPlanYet

from tests.application.test_plan_carousel import _make_plan
from tests.fakes import FakeCarouselRepository, FakeImageAIProvider, FakeTextAIProvider, SyncJobRunner


def _seed_generated_carousel(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    image_ai = FakeImageAIProvider()
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)
    plan = _make_plan(None)
    generate_images(
        state.id, plan, "low", repo=repo, media_storage=media_storage, image_ai=image_ai,
        job_runner=job_runner,
    )
    return repo, media_storage, job_runner, state.id


def test_regenerate_slides_applies_revision_and_rerenders(tmp_path):
    repo, media_storage, job_runner, cid = _seed_generated_carousel(tmp_path)
    revision = SlideRevision(headline="Nova", body="", visual_prompt="novo visual", swipe_cue="")
    text_ai = FakeTextAIProvider(revisions={1: revision})
    image_ai = FakeImageAIProvider()

    result = regenerate_slides(
        cid,
        [1],
        "deixa mais direto",
        repo=repo,
        media_storage=media_storage,
        text_ai=text_ai,
        image_ai=image_ai,
        job_runner=job_runner,
    )

    assert result.plan.slides[0].headline == "Nova"
    assert result.plan.slides[0].status == "done"
    assert text_ai.revise_calls == [([1], "deixa mais direto")]


def test_regenerate_slides_patches_element_content_preserving_user_layout(tmp_path):
    repo, media_storage, job_runner, cid = _seed_generated_carousel(tmp_path)

    # Simulate a manual edit made earlier in the layered editor: drag the
    # headline somewhere custom.
    state = repo.load(cid)
    headline = next(e for e in state.plan.slides[0].elements if e.role == "h1")
    headline.rect.x = 33.0
    repo.save(state)

    revision = SlideRevision(
        headline="Headline revisada pela IA", body="", visual_prompt="novo visual", swipe_cue=""
    )
    text_ai = FakeTextAIProvider(revisions={1: revision})
    image_ai = FakeImageAIProvider()

    result = regenerate_slides(
        cid, [1], "deixa mais direto",
        repo=repo, media_storage=media_storage, text_ai=text_ai, image_ai=image_ai,
        job_runner=job_runner,
    )

    patched_headline = next(e for e in result.plan.slides[0].elements if e.role == "h1")
    assert patched_headline.content == "Headline revisada pela IA"
    assert patched_headline.rect.x == 33.0


def test_regenerate_slides_raises_without_plan():
    repo = FakeCarouselRepository()
    text_ai = FakeTextAIProvider()
    image_ai = FakeImageAIProvider()
    job_runner = SyncJobRunner()
    state = create_carousel(repo=repo)

    with pytest.raises(NoPlanYet):
        regenerate_slides(
            state.id,
            [1],
            "",
            repo=repo,
            media_storage=None,
            text_ai=text_ai,
            image_ai=image_ai,
            job_runner=job_runner,
        )


def test_regenerate_slides_raises_on_invalid_indices(tmp_path):
    repo, media_storage, job_runner, cid = _seed_generated_carousel(tmp_path)
    text_ai = FakeTextAIProvider()
    image_ai = FakeImageAIProvider()

    with pytest.raises(InvalidSlideSelection):
        regenerate_slides(
            cid,
            [99],
            "",
            repo=repo,
            media_storage=media_storage,
            text_ai=text_ai,
            image_ai=image_ai,
            job_runner=job_runner,
        )


def test_regenerate_slides_raises_when_active(tmp_path):
    repo, media_storage, job_runner, cid = _seed_generated_carousel(tmp_path)
    job_runner._active.add(cid)
    text_ai = FakeTextAIProvider()
    image_ai = FakeImageAIProvider()

    with pytest.raises(GenerationInProgress):
        regenerate_slides(
            cid,
            [1],
            "",
            repo=repo,
            media_storage=media_storage,
            text_ai=text_ai,
            image_ai=image_ai,
            job_runner=job_runner,
        )
