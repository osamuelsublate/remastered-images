"""Disk-backed ``MediaStorage``: references, generated slides, user block
media and final exports as files.

On-disk layout: ``<cid>/references/``, ``<cid>/slides/``, ``<cid>/media/``
(user-uploaded image/video blocks) and ``<cid>/exports/`` (final composited
PNG/MP4 files that go into the download zip).
"""

from __future__ import annotations

import time
from pathlib import Path


class LocalMediaStorage:
    def __init__(self, carousels_dir: Path, media_url_prefix: str = "/media") -> None:
        self._carousels_dir = carousels_dir
        self._media_url_prefix = media_url_prefix.rstrip("/")

    def _carousel_dir(self, cid: str) -> Path:
        return self._carousels_dir / cid

    def _references_dir(self, cid: str) -> Path:
        return self._carousel_dir(cid) / "references"

    def _slides_dir(self, cid: str) -> Path:
        return self._carousel_dir(cid) / "slides"

    def save_reference(self, cid: str, filename: str, data: bytes) -> None:
        rdir = self._references_dir(cid)
        rdir.mkdir(parents=True, exist_ok=True)
        safe_name = filename.replace("/", "_")
        (rdir / safe_name).write_bytes(data)

    def list_reference_names(self, cid: str) -> list[str]:
        return [p.name for p in self.list_reference_paths(cid)]

    def list_reference_paths(self, cid: str) -> list[Path]:
        rdir = self._references_dir(cid)
        if not rdir.exists():
            return []
        return sorted(p for p in rdir.iterdir() if p.is_file())

    def slide_output_path(self, cid: str, index: int, ext: str) -> Path:
        sdir = self._slides_dir(cid)
        sdir.mkdir(parents=True, exist_ok=True)
        return sdir / f"slide-{index:02d}.{ext}"

    def list_slide_files(self, cid: str) -> list[Path]:
        sdir = self._slides_dir(cid)
        if not sdir.exists():
            return []
        return sorted(sdir.glob("slide-*.png")) + sorted(sdir.glob("slide-*.mp4"))

    def save_block_media(self, cid: str, filename: str, data: bytes) -> str:
        mdir = self._carousel_dir(cid) / "media"
        mdir.mkdir(parents=True, exist_ok=True)
        safe_name = filename.replace("/", "_").replace("\\", "_")
        # Timestamp prefix keeps names unique without clobbering re-uploads.
        unique = f"{int(time.time() * 1000)}-{safe_name}"
        (mdir / unique).write_bytes(data)
        return f"{self._media_url_prefix}/{cid}/media/{unique}"

    def export_output_path(self, cid: str, index: int, ext: str) -> Path:
        edir = self._carousel_dir(cid) / "exports"
        edir.mkdir(parents=True, exist_ok=True)
        return edir / f"slide-{index:02d}.{ext}"

    def list_export_files(self, cid: str) -> list[Path]:
        edir = self._carousel_dir(cid) / "exports"
        if not edir.exists():
            return []
        return sorted(edir.glob("slide-*"))

    def media_root(self) -> Path:
        return self._carousels_dir

    def public_url(self, cid: str, filename: str) -> str:
        return f"{self._media_url_prefix}/{cid}/slides/{filename}"
