"""Disk-backed ``CarouselRepository``: one JSON file per carousel.

Same on-disk layout as the pre-migration ``store.py`` (``<cid>/state.json``),
so carousels created before this refactor keep loading correctly.
"""

from __future__ import annotations

import os
import secrets
import tempfile
import time
from pathlib import Path

from ...domain.carousel import CarouselState


class FileCarouselRepository:
    def __init__(self, carousels_dir: Path) -> None:
        self._carousels_dir = carousels_dir

    def _carousel_dir(self, cid: str) -> Path:
        return self._carousels_dir / cid

    def _state_path(self, cid: str) -> Path:
        return self._carousel_dir(cid) / "state.json"

    def new_id(self) -> str:
        return secrets.token_hex(6)

    def create(self, cid: str) -> CarouselState:
        self._carousel_dir(cid).mkdir(parents=True, exist_ok=True)
        state = CarouselState(id=cid)
        self.save(state)
        return state

    def save(self, state: CarouselState) -> None:
        """Atomically persist state.

        A background worker thread and the request handlers may write/read
        this file concurrently. Writing to a unique temp file and then
        ``os.replace()`` (atomic rename) guarantees readers always see a
        complete file.
        """
        d = self._carousel_dir(state.id)
        d.mkdir(parents=True, exist_ok=True)
        path = self._state_path(state.id)
        fd, tmp_name = tempfile.mkstemp(dir=str(d), prefix=".state-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(state.model_dump_json(indent=2))
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def load(self, cid: str) -> CarouselState | None:
        path = self._state_path(cid)
        if not path.exists():
            return None
        # Resilient parse: tolerate a read that races a concurrent write.
        last_exc: Exception | None = None
        for _ in range(5):
            try:
                text = path.read_text(encoding="utf-8")
                if text.strip():
                    return CarouselState.model_validate_json(text)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
            time.sleep(0.05)
        if last_exc is not None:
            raise last_exc
        return None
