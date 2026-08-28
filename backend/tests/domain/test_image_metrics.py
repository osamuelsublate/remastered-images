import random

from PIL import Image

from app.domain.image_metrics import analyze_slide_image, metrics_prompt_block


def _half_flat_half_noise(path, size=(480, 600)):
    """Left half: flat dark. Right half: per-pixel noise (visually busy)."""
    img = Image.new("RGB", size, (20, 20, 20))
    rnd = random.Random(42)
    half_w = size[0] // 2
    noise = Image.frombytes(
        "L", (half_w, size[1]), bytes(rnd.getrandbits(8) for _ in range(half_w * size[1]))
    )
    img.paste(noise.convert("RGB"), (half_w, 0))
    img.save(path)
    return path


def _top_white_bottom_black(path, size=(480, 600)):
    img = Image.new("RGB", size, (0, 0, 0))
    img.paste(Image.new("RGB", (size[0], size[1] // 2), (255, 255, 255)), (0, 0))
    img.save(path)
    return path


def test_edge_density_grid_flags_the_noisy_half(tmp_path):
    metrics = analyze_slide_image(_half_flat_half_noise(tmp_path / "img.png"))

    left_density, _ = metrics.region_stats(0, 0, 45, 100)
    right_density, _ = metrics.region_stats(55, 0, 45, 100)
    assert left_density < 5
    assert right_density > 20
    assert right_density > left_density * 4


def test_luminance_grid_tracks_brightness(tmp_path):
    metrics = analyze_slide_image(_top_white_bottom_black(tmp_path / "img.png"))

    _, top_lum = metrics.region_stats(0, 0, 100, 40)
    _, bottom_lum = metrics.region_stats(0, 60, 100, 40)
    assert top_lum > 240
    assert bottom_lum < 15


def test_best_region_picks_the_calm_side(tmp_path):
    metrics = analyze_slide_image(_half_flat_half_noise(tmp_path / "img.png"))

    x, y = metrics.best_region(40, 30)

    # A 40%-wide window must land fully inside the flat left half.
    assert x + 40 <= 55
    assert 0 <= y <= 70


def test_best_region_respects_y_band_and_margin(tmp_path):
    metrics = analyze_slide_image(_half_flat_half_noise(tmp_path / "img.png"))

    x, y = metrics.best_region(30, 20, y_band=(50, 80), x_margin=8.9)

    assert y >= 50
    assert y <= 80
    assert x >= 8.9


def test_metrics_prompt_block_is_compact_digit_grid(tmp_path):
    metrics = analyze_slide_image(_half_flat_half_noise(tmp_path / "img.png"))

    block = metrics_prompt_block(metrics)

    assert "12 cols x 15 rows" in block
    lines = block.splitlines()
    digit_rows = [ln for ln in lines if ln and all(c.isdigit() for c in ln)]
    # One 15-row grid for activity + one for luminance.
    assert len(digit_rows) == 30
    assert all(len(ln) == 12 for ln in digit_rows)
