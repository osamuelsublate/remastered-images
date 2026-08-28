"""Port for rendering slide media via Remotion (MP4 clips and still PNGs)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class VideoRenderer(Protocol):
    def render(self, props: dict, output_path: Path) -> None: ...

    def render_still(self, props: dict, output_path: Path) -> None:
        """Render the final composited frame of a slide to a PNG."""
        ...
