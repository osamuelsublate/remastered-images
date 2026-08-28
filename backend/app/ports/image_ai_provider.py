"""Port for the image-generation AI provider."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ImageAIProvider(Protocol):
    def generate_slide_image(
        self,
        *,
        prompt: str,
        output_path: Path,
        references: list[Path] | None = None,
        quality: str | None = None,
    ) -> None: ...

    def generate_asset_image(
        self,
        *,
        prompt: str,
        output_path: Path,
        quality: str | None = None,
    ) -> None:
        """Generate ONE isolated block asset (icon/illustration) with a
        transparent background — separate model/pipeline from the opaque
        full-bleed slide background (see ``generate_slide_image``)."""
        ...
