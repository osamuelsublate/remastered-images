"""Port for storing/serving carousel media (reference uploads, generated
slide PNGs/MP4s).

Kept separate from ``CarouselRepository`` on purpose: a future SQL repository
would still likely keep binaries on disk (or object storage), so the two are
independent axes of change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class MediaStorage(Protocol):
    def save_reference(self, cid: str, filename: str, data: bytes) -> None: ...

    def list_reference_names(self, cid: str) -> list[str]: ...

    def list_reference_paths(self, cid: str) -> list[Path]: ...

    def slide_output_path(self, cid: str, index: int, ext: str) -> Path: ...

    def list_slide_files(self, cid: str) -> list[Path]: ...

    def save_block_media(self, cid: str, filename: str, data: bytes) -> str:
        """Store a user-uploaded image/video block asset; returns its public URL."""
        ...

    def export_output_path(self, cid: str, index: int, ext: str) -> Path: ...

    def list_export_files(self, cid: str) -> list[Path]: ...

    def media_root(self) -> Path: ...

    def public_url(self, cid: str, filename: str) -> str: ...
