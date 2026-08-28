"""Composition root.

Instantiates the concrete adapters behind each port and exposes them as
FastAPI dependency providers. Each provider is cached (module-level
singleton) so stateful adapters like the job runner are shared across
requests within the process.

Tests swap in fakes/temp storage via ``app.dependency_overrides`` targeting
these exact functions — no environment-variable timing tricks needed.
"""

from __future__ import annotations

from functools import lru_cache

from ..adapters.ai.openrouter_audio_transcription_provider import (
    OpenRouterAudioTranscriptionProvider,
)
from ..adapters.ai.openrouter_image_provider import OpenRouterImageProvider
from ..adapters.ai.openrouter_text_provider import OpenRouterTextProvider
from ..adapters.jobs.thread_job_runner import ThreadJobRunner
from ..adapters.rendering.remotion_subprocess_renderer import RemotionSubprocessRenderer
from ..adapters.repositories.file_carousel_repository import FileCarouselRepository
from ..adapters.storage.local_media_storage import LocalMediaStorage
from ..config import Settings, load_settings
from ..ports.audio_transcription_provider import AudioTranscriptionProvider
from ..ports.carousel_repository import CarouselRepository
from ..ports.image_ai_provider import ImageAIProvider
from ..ports.job_runner import JobRunner
from ..ports.media_storage import MediaStorage
from ..ports.text_ai_provider import TextAIProvider
from ..ports.video_renderer import VideoRenderer


@lru_cache
def get_settings() -> Settings:
    return load_settings()


@lru_cache
def get_carousel_repository() -> CarouselRepository:
    return FileCarouselRepository(get_settings().carousels_dir)


@lru_cache
def get_media_storage() -> MediaStorage:
    return LocalMediaStorage(get_settings().carousels_dir)


@lru_cache
def get_text_ai_provider() -> TextAIProvider:
    settings = get_settings()
    return OpenRouterTextProvider(
        api_key=settings.openrouter_api_key,
        planning_model=settings.planning_model,
        chat_model=settings.chat_model,
        base_url=settings.openrouter_base_url,
    )


@lru_cache
def get_transcription_ai_provider() -> AudioTranscriptionProvider:
    settings = get_settings()
    return OpenRouterAudioTranscriptionProvider(
        api_key=settings.openrouter_api_key,
        model=settings.transcription_model,
        base_url=settings.openrouter_base_url,
    )


@lru_cache
def get_image_ai_provider() -> ImageAIProvider:
    settings = get_settings()
    return OpenRouterImageProvider(
        api_key=settings.openrouter_api_key,
        model=settings.image_model,
        image_size=settings.image_size,
        default_quality=settings.default_quality,
        asset_model=settings.asset_image_model,
        fallback_model=settings.image_fallback_model,
        base_url=settings.openrouter_base_url,
    )


@lru_cache
def get_video_renderer() -> VideoRenderer:
    settings = get_settings()
    return RemotionSubprocessRenderer(
        node_bin=settings.node_bin,
        render_script=settings.remotion_render_script,
        cwd=settings.remotion_dir,
        timeout=settings.render_timeout,
    )


@lru_cache
def get_job_runner() -> JobRunner:
    return ThreadJobRunner()
