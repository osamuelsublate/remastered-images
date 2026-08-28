"""Subprocess-based ``VideoRenderer``: invokes the Remotion Node renderer."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


class RemotionSubprocessRenderer:
    def __init__(self, node_bin: str, render_script: Path, cwd: Path, timeout: float) -> None:
        self._node_bin = node_bin
        self._render_script = render_script
        self._cwd = cwd
        self._timeout = timeout

    def render(self, props: dict, output_path: Path) -> None:
        """Invoke the Node renderer for a single clip. Raises on failure."""
        self._invoke(props, output_path)

    def render_still(self, props: dict, output_path: Path) -> None:
        """Render the final composited frame to a PNG (render.mjs switches to
        ``renderStill`` based on the output extension)."""
        self._invoke(props, output_path)

    def _invoke(self, props: dict, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix="props-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(props, f, ensure_ascii=False)
            proc = subprocess.run(
                [self._node_bin, str(self._render_script), tmp, str(output_path)],
                cwd=str(self._cwd),
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").strip().splitlines()
                tail = " | ".join(err[-5:]) if err else "erro desconhecido"
                raise RuntimeError(f"Falha no render Remotion: {tail}")
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
