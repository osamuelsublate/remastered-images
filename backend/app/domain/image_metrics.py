"""Image analysis for content-aware text placement.

Turns a generated slide background into a small grid of per-cell metrics
(edge density = visual activity, luminance, average color) using pure
Pillow — no numpy/OpenCV. The grid serves two purposes:

1. It is serialized into the layout-vision agent's prompt
   (``metrics_prompt_block``), anchoring the model's coordinate reasoning in
   real measurements of the actual pixels (vision models alone are known to
   drift on coordinates).
2. It powers the deterministic fallback (``ImageMetrics.best_region``) and
   the contrast validation (``region_stats``) when the vision call fails or
   returns something unusable.

The approach mirrors the classic saliency/negative-space pipelines
(SmartText ICME'20, LayoutDiT): text goes where the image is calm.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

try:
    from PIL import Image, ImageFilter
except ImportError as exc:  # pragma: no cover
    raise ImportError("Pillow is required: pip install Pillow") from exc

# 12x15 cells over a 1080x1350 canvas = 90x90px per cell — fine enough to
# localize negative space, small enough to serialize into a prompt.
DEFAULT_COLS = 12
DEFAULT_ROWS = 15


class ImageMetrics(BaseModel):
    """Per-cell metrics of a slide background, grid indexed [row][col]."""

    cols: int
    rows: int
    # 0-100: mean edge-filter response per cell (0 = flat/calm, 100 = busy).
    edge_density: list[list[int]]
    # 0-255: mean luminance per cell.
    luminance: list[list[int]]
    # Mean RGB per cell.
    avg_color: list[list[list[int]]]

    def _cell_range(self, rect_x: float, rect_y: float, rect_w: float, rect_h: float):
        """Cell index bounds (inclusive) covered by a percent-based rect."""
        col0 = max(0, min(self.cols - 1, int(rect_x / 100 * self.cols)))
        col1 = max(0, min(self.cols - 1, int((rect_x + rect_w) / 100 * self.cols - 1e-9)))
        row0 = max(0, min(self.rows - 1, int(rect_y / 100 * self.rows)))
        row1 = max(0, min(self.rows - 1, int((rect_y + rect_h) / 100 * self.rows - 1e-9)))
        return row0, row1, col0, col1

    def region_stats(
        self, x: float, y: float, w: float, h: float
    ) -> tuple[float, float]:
        """(mean edge density 0-100, mean luminance 0-255) inside a percent rect."""
        row0, row1, col0, col1 = self._cell_range(x, y, w, h)
        densities: list[int] = []
        lums: list[int] = []
        for r in range(row0, row1 + 1):
            for c in range(col0, col1 + 1):
                densities.append(self.edge_density[r][c])
                lums.append(self.luminance[r][c])
        n = len(densities) or 1
        return sum(densities) / n, sum(lums) / n

    def best_region(
        self,
        w: float,
        h: float,
        y_band: tuple[float, float] = (0.0, 100.0),
        x_margin: float = 0.0,
    ) -> tuple[float, float]:
        """(x, y) of the calmest ``w x h`` percent window whose top edge lies
        within ``y_band``. Deterministic fallback when the vision agent is
        unavailable: scans window positions cell by cell and picks the one
        with the lowest mean edge density (ties resolved toward the top-left,
        which reads most naturally)."""
        cell_w = 100.0 / self.cols
        cell_h = 100.0 / self.rows
        best_xy = (x_margin, max(y_band[0], 0.0))
        best_score = float("inf")
        y = max(y_band[0], 0.0)
        while y <= min(y_band[1], 100.0 - h):
            x = x_margin
            while x <= 100.0 - w - x_margin + 1e-9:
                density, _ = self.region_stats(x, y, w, h)
                if density < best_score - 1e-9:
                    best_score = density
                    best_xy = (x, y)
                x += cell_w
            y += cell_h
        return best_xy


def analyze_slide_image(
    image_path: Path, cols: int = DEFAULT_COLS, rows: int = DEFAULT_ROWS
) -> ImageMetrics:
    """Compute the metrics grid for one slide background PNG.

    ``Image.BOX`` resize averages every source pixel inside each target cell
    — equivalent to integral-image pooling, in three lines of Pillow.
    """
    img = Image.open(image_path).convert("RGB")
    gray = img.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)

    edge_small = edges.resize((cols, rows), Image.BOX)
    lum_small = gray.resize((cols, rows), Image.BOX)
    rgb_small = img.resize((cols, rows), Image.BOX)

    edge_density = [
        [round(edge_small.getpixel((c, r)) / 255 * 100) for c in range(cols)]
        for r in range(rows)
    ]
    luminance = [
        [int(lum_small.getpixel((c, r))) for c in range(cols)] for r in range(rows)
    ]
    avg_color = [
        [list(rgb_small.getpixel((c, r))) for c in range(cols)] for r in range(rows)
    ]
    return ImageMetrics(
        cols=cols,
        rows=rows,
        edge_density=edge_density,
        luminance=luminance,
        avg_color=avg_color,
    )


def metrics_prompt_block(metrics: ImageMetrics) -> str:
    """Compact textual grid for the vision agent's prompt.

    Each cell becomes a single digit 0-9 so a 12x15 grid costs ~2 short
    lines of tokens per map, yet gives the model hard numbers about where
    the image is busy/calm and dark/bright.
    """
    cell_w = 100.0 / metrics.cols
    cell_h = 100.0 / metrics.rows

    def _digit_rows(grid: list[list[int]], scale: float) -> str:
        return "\n".join(
            "".join(str(min(9, round(v / scale))) for v in row) for row in grid
        )

    return (
        f"IMAGE METRICS GRID ({metrics.cols} cols x {metrics.rows} rows; each cell = "
        f"{cell_w:.1f}% wide x {cell_h:.1f}% tall; row 1 = top of the image).\n"
        "VISUAL ACTIVITY (0=flat/empty, 9=busy/detailed — place text on the "
        "LOWEST digits):\n"
        f"{_digit_rows(metrics.edge_density, 100 / 9)}\n"
        "LUMINANCE (0=dark, 9=bright — affects which palette color stays "
        "readable):\n"
        f"{_digit_rows(metrics.luminance, 255 / 9)}"
    )
