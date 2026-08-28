import pytest

from app.adapters.storage.local_media_storage import LocalMediaStorage
from app.application.use_cases.create_carousel import create_carousel
from app.application.use_cases.generate_block_image import generate_block_image
from app.domain.errors import CarouselNotFound, InvalidSlideSelection, NoPlanYet

from tests.application.test_plan_carousel import _make_plan
from tests.fakes import FakeCarouselRepository, FakeImageAIProvider, FakeTextAIProvider


def _seed(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    state = create_carousel(repo=repo)
    state.plan = _make_plan(None)
    repo.save(state)
    return repo, media_storage, state


def test_generate_block_image_returns_url_and_saves_file(tmp_path):
    repo, media_storage, state = _seed(tmp_path)
    text_ai = FakeTextAIProvider()
    image_ai = FakeImageAIProvider()

    url, kind = generate_block_image(
        state.id,
        1,
        "um foguete",
        repo=repo,
        media_storage=media_storage,
        text_ai=text_ai,
        image_ai=image_ai,
    )

    assert kind == "image"
    assert url.startswith(f"/media/{state.id}/media/")
    saved = list((tmp_path / state.id / "media").iterdir())
    assert len(saved) == 1
    assert saved[0].read_bytes() == b"fake-transparent-png-bytes"


def test_generate_block_image_crafts_prompt_before_generating(tmp_path):
    """The asset agent (craft_asset_prompt) must run first, with the
    carousel's art direction and the target slide, and its output — not the
    raw user text — is what reaches the image model."""
    repo, media_storage, state = _seed(tmp_path)
    text_ai = FakeTextAIProvider(asset_prompt_factory=lambda req: f"DIRECTED: {req}")
    image_ai = FakeImageAIProvider()

    generate_block_image(
        state.id,
        1,
        "um foguete",
        repo=repo,
        media_storage=media_storage,
        text_ai=text_ai,
        image_ai=image_ai,
    )

    assert len(text_ai.asset_prompt_calls) == 1
    user_request, art_direction, slide = text_ai.asset_prompt_calls[0]
    assert user_request == "um foguete"
    assert art_direction.model_dump() == state.plan.art_direction.model_dump()
    assert slide.index == 1
    assert slide.headline == "H"

    assert len(image_ai.asset_calls) == 1
    crafted_prompt, _ = image_ai.asset_calls[0]
    assert crafted_prompt == "DIRECTED: um foguete"


def test_generate_block_image_raises_when_carousel_missing(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)

    with pytest.raises(CarouselNotFound):
        generate_block_image(
            "does-not-exist",
            1,
            "um foguete",
            repo=repo,
            media_storage=media_storage,
            text_ai=FakeTextAIProvider(),
            image_ai=FakeImageAIProvider(),
        )


def test_generate_block_image_raises_when_no_plan(tmp_path):
    repo = FakeCarouselRepository()
    media_storage = LocalMediaStorage(tmp_path)
    state = create_carousel(repo=repo)

    with pytest.raises(NoPlanYet):
        generate_block_image(
            state.id,
            1,
            "um foguete",
            repo=repo,
            media_storage=media_storage,
            text_ai=FakeTextAIProvider(),
            image_ai=FakeImageAIProvider(),
        )


def test_generate_block_image_raises_for_invalid_slide_index(tmp_path):
    repo, media_storage, state = _seed(tmp_path)

    with pytest.raises(InvalidSlideSelection):
        generate_block_image(
            state.id,
            99,
            "um foguete",
            repo=repo,
            media_storage=media_storage,
            text_ai=FakeTextAIProvider(),
            image_ai=FakeImageAIProvider(),
        )
