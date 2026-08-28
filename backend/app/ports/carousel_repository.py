"""Port for persisting carousel state (metadata, not media binaries).

The disk-backed implementation lives in
``adapters/repositories/file_carousel_repository.py``. A future SQL-backed
implementation only needs to satisfy this contract.
"""

from __future__ import annotations

from typing import Protocol

from ..domain.carousel import CarouselState


class CarouselRepository(Protocol):
    def new_id(self) -> str: ...

    def create(self, cid: str) -> CarouselState: ...

    def save(self, state: CarouselState) -> None: ...

    def load(self, cid: str) -> CarouselState | None: ...
