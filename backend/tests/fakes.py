"""In-memory fakes satisfying the application ports, for tests.

Used both by the API-level characterization tests (via
``app.dependency_overrides``) and by the use-case unit tests.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from app.domain.carousel import ArtDirection, Brief, CarouselPlan, CarouselState, Slide, SlideRevision
from app.domain.layout_refine import TextPlacement


class FakeCarouselRepository:
    """Pure in-memory ``CarouselRepository`` — no disk I/O at all."""

    def __init__(self) -> None:
        self._states: dict[str, CarouselState] = {}
        self._counter = 0

    def new_id(self) -> str:
        self._counter += 1
        return f"fake-{self._counter}"

    def create(self, cid: str) -> CarouselState:
        state = CarouselState(id=cid)
        self._states[cid] = state
        return state.model_copy(deep=True)

    def save(self, state: CarouselState) -> None:
        self._states[state.id] = state.model_copy(deep=True)

    def load(self, cid: str) -> CarouselState | None:
        state = self._states.get(cid)
        return state.model_copy(deep=True) if state is not None else None


class _FakeChatTurnStream:
    """In-memory stand-in for ``ChatTurnStream``: yields the whole text as a
    single chunk (good enough for tests that don't care about delta
    granularity) and returns ``(text, plan)`` from ``result()``.
    """

    def __init__(self, text: str, plan: CarouselPlan | None) -> None:
        self._text = text
        self._plan = plan

    def __iter__(self):
        if self._text:
            yield self._text

    def result(self) -> tuple[str, CarouselPlan | None]:
        return self._text, self._plan


class FakeTextAIProvider:
    def __init__(
        self,
        plan_factory: Callable[[Brief], CarouselPlan] | None = None,
        chat_factory: Callable[..., tuple[str, CarouselPlan | None]] | None = None,
        revisions: dict[int, SlideRevision] | None = None,
        asset_prompt_factory: Callable[[str], str] | None = None,
        layout_factory: Callable[[Slide], list[TextPlacement]] | None = None,
    ) -> None:
        self._plan_factory = plan_factory
        self._chat_factory = chat_factory
        self._revisions = revisions or {}
        self._asset_prompt_factory = asset_prompt_factory
        self._layout_factory = layout_factory
        self.plan_calls: list[Brief] = []
        self.revise_calls: list[tuple[list[int], str]] = []
        self.asset_prompt_calls: list[tuple[str, ArtDirection, Slide]] = []
        self.layout_calls: list[Slide] = []

    def plan_carousel(self, brief: Brief) -> CarouselPlan:
        self.plan_calls.append(brief)
        if self._plan_factory is None:
            raise AssertionError("FakeTextAIProvider.plan_carousel not configured")
        return self._plan_factory(brief)

    def chat_turn_stream(self, history, *, current_plan=None, references=None):
        if self._chat_factory is not None:
            text, plan = self._chat_factory(
                history, current_plan=current_plan, references=references
            )
        else:
            text, plan = ("ok", None)
        return _FakeChatTurnStream(text, plan)

    def revise_slides(
        self, plan: CarouselPlan, indices: list[int], instruction: str
    ) -> dict[int, SlideRevision]:
        self.revise_calls.append((indices, instruction))
        return self._revisions

    def craft_asset_prompt(
        self, user_request: str, *, art_direction: ArtDirection, slide: Slide
    ) -> str:
        self.asset_prompt_calls.append((user_request, art_direction, slide))
        if self._asset_prompt_factory is not None:
            return self._asset_prompt_factory(user_request)
        return f"crafted asset prompt: {user_request}"

    def suggest_text_layout(
        self,
        *,
        image_png: bytes,
        metrics_block: str,
        slide: Slide,
        art_direction: ArtDirection,
        total: int,
    ) -> list[TextPlacement]:
        self.layout_calls.append(slide)
        if self._layout_factory is not None:
            return self._layout_factory(slide)
        placements = [
            TextPlacement(target="h1", x=10, y=10, w=80, font_size=64, color="#ffffff")
        ]
        if slide.body.strip():
            placements.append(
                TextPlacement(target="body", x=10, y=40, w=70, font_size=32, color="#ffffff")
            )
        return placements


class _FakeTranscriptionStream:
    """In-memory stand-in for ``TranscriptionStream``."""

    def __init__(self, chunks: list[str], final_text: str | None = None) -> None:
        self._chunks = chunks
        self._final_text = final_text if final_text is not None else "".join(chunks)

    def __iter__(self):
        return iter(self._chunks)

    def result(self) -> str:
        return self._final_text


class FakeAudioTranscriptionProvider:
    def __init__(self, chunks: list[str] | None = None, fail: bool = False) -> None:
        self._chunks = chunks if chunks is not None else ["ok"]
        self._fail = fail
        self.calls: list[tuple[bytes, str]] = []

    def transcribe_stream(self, audio_bytes: bytes, filename: str) -> _FakeTranscriptionStream:
        self.calls.append((audio_bytes, filename))
        if self._fail:
            raise RuntimeError("transcription provider down")
        return _FakeTranscriptionStream(self._chunks)


class FakeImageAIProvider:
    def __init__(self, delay: float = 0.0, fail_indices: set[int] | None = None) -> None:
        self.delay = delay
        self.calls: list[Path] = []
        self.asset_calls: list[tuple[str, Path]] = []

    def generate_slide_image(
        self, *, prompt: str, output_path: Path, references=None, quality=None
    ) -> None:
        self.calls.append(output_path)
        if self.delay:
            time.sleep(self.delay)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-png-bytes")

    def generate_asset_image(self, *, prompt: str, output_path: Path, quality=None) -> None:
        self.asset_calls.append((prompt, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-transparent-png-bytes")


class FakeVideoRenderer:
    def __init__(self) -> None:
        self.calls: list[tuple[dict, Path]] = []
        self.still_calls: list[tuple[dict, Path]] = []

    def render(self, props: dict, output_path: Path) -> None:
        self.calls.append((props, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-mp4-bytes")

    def render_still(self, props: dict, output_path: Path) -> None:
        self.still_calls.append((props, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-png-still-bytes")


class SyncJobRunner:
    """Runs ``fn`` synchronously (no thread) so unit tests stay deterministic."""

    def __init__(self) -> None:
        self._active: set[str] = set()
        self._lock = threading.Lock()

    def is_active(self, key: str) -> bool:
        with self._lock:
            return key in self._active

    def submit(self, key: str, fn: Callable[[], None]) -> bool:
        with self._lock:
            if key in self._active:
                return False
            self._active.add(key)
        try:
            fn()
        finally:
            with self._lock:
                self._active.discard(key)
        return True
