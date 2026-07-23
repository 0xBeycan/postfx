import numpy as np
import pytest


@pytest.fixture
def rgb_image():
    """Deterministic synthetic RGB test image (gradient + color blocks)."""
    rng = np.random.default_rng(0)
    h, w = 128, 96
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    xs = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    img = np.stack([
        ys * np.ones_like(xs),
        xs * np.ones_like(ys),
        0.5 * np.ones((h, w), np.float32),
    ], axis=2)
    img = np.clip(img + 0.05 * rng.standard_normal((h, w, 3)).astype(np.float32),
                  0.0, 1.0)
    return img.astype(np.float32)
