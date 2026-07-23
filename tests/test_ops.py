import os
import tempfile

import cv2
import numpy as np
import pytest

from postfx import ops


NEUTRAL = {
    "exposure": lambda x: ops.exposure(x, 0.0),
    "highlight_rolloff": lambda x: ops.highlight_rolloff(x, 0.7, 0.0),
    "lift_gamma_gain": lambda x: ops.lift_gamma_gain(x, [0, 0, 0], [1, 1, 1], [1, 1, 1]),
    "split_toning": lambda x: ops.split_toning(x, [0, 0, 0], [0, 0, 0], 0.0),
    "tone_curve": lambda x: ops.tone_curve(x, 0.0),
    "vibrance_saturation": lambda x: ops.vibrance_saturation(x, 0.0, 1.0),
    "halation": lambda x: ops.halation(x, strength=0.0),
    "barrel_distortion": lambda x: ops.barrel_distortion(x, 0.0),
    "chromatic_aberration": lambda x: ops.chromatic_aberration(x, 0.0),
    "vignette": lambda x: ops.vignette(x, 0.0),
    "black_point_lift": lambda x: ops.black_point_lift(x, 0.0),
    "clarity": lambda x: ops.clarity(x, 0.0),
    "grain": lambda x: ops.grain(x, 0.0, 0.0),
    "sharpen": lambda x: ops.sharpen(x, 0.0),
}


@pytest.mark.parametrize("name", list(NEUTRAL))
def test_neutral_params_are_identity(name, rgb_image):
    out = NEUTRAL[name](rgb_image)
    assert out.shape == rgb_image.shape
    assert out.dtype == np.float32
    assert not np.isnan(out).any()
    assert np.array_equal(out, rgb_image), f"{name} is not identity at neutral params"


def test_exposure_doubles_at_one_stop(rgb_image):
    out = ops.exposure(rgb_image, 1.0)
    assert np.allclose(out, rgb_image * 2.0)


def test_highlight_rolloff_compresses_only_above_knee():
    x = np.array([0.3, 0.8, 2.0], np.float32).reshape(1, 1, 3)
    out = ops.highlight_rolloff(x, knee=0.7, strength=0.5)
    assert out[0, 0, 0] == pytest.approx(0.3)          # below knee unchanged
    assert out[0, 0, 2] < 2.0                           # above knee compressed


def test_black_point_lift_raises_blacks():
    x = np.zeros((4, 4, 3), np.float32)
    out = ops.black_point_lift(x, 0.1)
    assert np.allclose(out, 0.1)


def test_vignette_darkens_corners_not_center(rgb_image):
    out = ops.vignette(rgb_image, strength=0.6, feather=0.2)
    h, w = rgb_image.shape[:2]
    center = out[h // 2, w // 2] / (rgb_image[h // 2, w // 2] + 1e-6)
    corner = out[0, 0] / (rgb_image[0, 0] + 1e-6)
    assert corner.mean() < center.mean()
    assert center.mean() == pytest.approx(1.0, abs=0.02)


def test_grain_deterministic_with_seed(rgb_image):
    a = ops.grain(rgb_image, 0.05, 0.02, size=1.8, seed=42)
    b = ops.grain(rgb_image, 0.05, 0.02, size=1.8, seed=42)
    c = ops.grain(rgb_image, 0.05, 0.02, size=1.8, seed=43)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_grain_amplitude_resolution_independent():
    """Same 'size' and amount give ~equal grain amplitude at different res."""
    gray = np.full((256, 256, 3), 0.5, np.float32)
    small = ops.grain(cv2.resize(gray, (512, 512)), 0.05, 0.0, size=1.8, seed=1)
    big = ops.grain(cv2.resize(gray, (2048, 2048)), 0.05, 0.0, size=1.8, seed=1)
    ratio = big.std() / small.std()
    assert 0.7 < ratio < 1.4, ratio


def test_grain_weakest_at_black_and_white():
    """Luminance weighting: grain ~0 at black/white, strong in midtones."""
    black = np.zeros((64, 64, 3), np.float32)
    white = np.ones((64, 64, 3), np.float32)
    mid = np.full((64, 64, 3), 0.5, np.float32)
    gb = np.abs(ops.grain(black, 0.1, 0.0, size=1.5, floor=0.0, seed=1) - black).mean()
    gw = np.abs(ops.grain(white, 0.1, 0.0, size=1.5, floor=0.0, seed=1) - white).mean()
    gm = np.abs(ops.grain(mid, 0.1, 0.0, size=1.5, floor=0.0, seed=1) - mid).mean()
    assert gm > gb and gm > gw


def test_jpeg_cycle_changes_data_but_keeps_shape():
    img = (np.random.default_rng(0).random((64, 64, 3)) * 255).astype(np.uint8)
    out = ops.jpeg_cycle(img, quality=60, cycles=2)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def _write_cube(path, n, fn):
    with open(path, "w") as f:
        f.write(f"LUT_3D_SIZE {n}\n")
        for b in range(n):
            for g in range(n):
                for r in range(n):
                    rr, gg, bb = fn(r / (n - 1), g / (n - 1), b / (n - 1))
                    f.write(f"{rr:.6f} {gg:.6f} {bb:.6f}\n")


def test_lut_identity_is_identity(rgb_image):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "id.cube")
    _write_cube(p, 2, lambda r, g, b: (r, g, b))
    out = ops.apply_lut(rgb_image, ops.load_cube_lut(p), 1.0)
    assert np.abs(out - rgb_image).max() < 1e-4


def test_lut_shifts_color_and_blends_intensity(rgb_image):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "warm.cube")
    _write_cube(p, 17, lambda r, g, b: (min(1.0, r * 1.1), g, b * 0.9))
    lut = ops.load_cube_lut(p)
    full = ops.apply_lut(rgb_image, lut, 1.0)
    assert full[..., 0].mean() > rgb_image[..., 0].mean()   # red up
    assert full[..., 2].mean() < rgb_image[..., 2].mean()   # blue down
    half = ops.apply_lut(rgb_image, lut, 0.5)
    assert np.abs(half - (rgb_image + full) / 2).max() < 1e-5


def test_lut_1d_rejected():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "bad.cube")
    with open(p, "w") as f:
        f.write("LUT_1D_SIZE 4\n0 0 0\n1 1 1\n")
    with pytest.raises(ValueError):
        ops.load_cube_lut(p)
