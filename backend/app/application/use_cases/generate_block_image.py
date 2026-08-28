"""Use case: generate an isolated, transparent-background block asset
(icon/illustration) for the "Criar imagem" editor action.

Separate from the slide background pipeline (``regenerate_slides``/
``generate_carousel``): the user's short free-text idea is first refined by a
dedicated agent (``TextAIProvider.craft_asset_prompt``) into a fully-directed
image prompt — aware of the carousel's design references (palette/icon_style)
and the specific slide the asset will complement — before gpt-image-1.5
renders it with a transparent background. The result is stored through the
same media pool as manual uploads (``upload_block_media``), so it comes back
in the exact same ``(url, kind)`` shape ready to become an ``image`` block.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ...domain.errors import CarouselNotFound, InvalidSlideSelection, NoPlanYet
from ...ports.carousel_repository import CarouselRepository
from ...ports.image_ai_provider import ImageAIProvider
from ...ports.media_storage import MediaStorage
from ...ports.text_ai_provider import TextAIProvider


def generate_block_image(
    cid: str,
    slide_index: int,
    user_prompt: str,
    *,
    repo: CarouselRepository,
    media_storage: MediaStorage,
    text_ai: TextAIProvider,
    image_ai: ImageAIProvider,
) -> tuple[str, str]:
    """Returns ``(public_url, "image")`` — same shape as ``upload_block_media``."""
    state = repo.load(cid)
    if state is None:
        raise CarouselNotFound(cid)
    if state.plan is None:
        raise NoPlanYet("Nenhum plano para gerar um ativo.")

    total = len(state.plan.slides)
    if not (1 <= slide_index <= total):
        raise InvalidSlideSelection("Slide inválido.")

    slide = state.plan.slides[slide_index - 1]
    crafted_prompt = text_ai.craft_asset_prompt(
        user_prompt, art_direction=state.plan.art_direction, slide=slide
    )

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        image_ai.generate_asset_image(prompt=crafted_prompt, output_path=tmp_path)
        data = tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)

    url = media_storage.save_block_media(cid, "asset.png", data)
    return url, "image"
