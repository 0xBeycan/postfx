import numpy as np
import pytest

from postfx import get_condition, load_theme
from postfx.pipeline import process, resolve_theme
from postfx.theme import list_theme_files


ALL_THEMES = [load_theme(p) for p in list_theme_files()]


@pytest.mark.parametrize("theme", ALL_THEMES, ids=lambda t: t["name"])
def test_pipeline_preserves_shape_dtype_range(theme, rgb_image):
    out = process(rgb_image, theme, get_condition("indoor_evening"), 1.0, 7)
    assert out.shape == rgb_image.shape            # resolution & aspect preserved
    assert out.dtype == np.float32
    assert not np.isnan(out).any()
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_strength_zero_returns_original(rgb_image):
    theme = load_theme("cinematic_teal_orange")
    out = process(rgb_image, theme, get_condition("night_flash"), 0.0, 7)
    assert np.array_equal(out, rgb_image)


def test_strength_scales_effect(rgb_image):
    theme = load_theme("ektar_100")
    condition = get_condition("indoor_evening")
    half = process(rgb_image, theme, condition, 0.5, 7)
    full = process(rgb_image, theme, condition, 1.0, 7)
    assert np.abs(half - rgb_image).mean() < np.abs(full - rgb_image).mean()


def test_pipeline_deterministic(rgb_image):
    theme = load_theme("cinestill_800t")
    condition = get_condition("night_flash")
    a = process(rgb_image, theme, condition, 1.0, 99)
    b = process(rgb_image, theme, condition, 1.0, 99)
    assert np.array_equal(a, b)


def test_condition_night_flash_grainier_than_day(rgb_image):
    theme = load_theme("tri_x_400")
    day = process(rgb_image, theme, get_condition("day_outdoor"), 1.0, 5)
    night = process(rgb_image, theme, get_condition("night_flash"), 1.0, 5)
    assert np.abs(night - rgb_image).std() > np.abs(day - rgb_image).std()


def test_condition_neutral_is_identity_multiplier(rgb_image):
    """The 'neutral' condition scales nothing: all three multipliers are 1.0."""
    cond = get_condition("neutral")
    assert cond == {"grain": 1.0, "chroma_noise": 1.0, "halation": 1.0}
    # None resolves to the default, which is neutral.
    assert get_condition(None) == cond


def test_bw_theme_is_grayscale(rgb_image):
    """tri_x_400 uses saturation 0 -> channels should be ~equal (grayscale)."""
    out = process(rgb_image, load_theme("tri_x_400"), get_condition("day_outdoor"),
                  1.0, 0)
    ch_spread = np.abs(out - out.mean(axis=2, keepdims=True)).mean()
    assert ch_spread < 0.02


def test_themes_produce_distinct_output(rgb_image):
    condition = get_condition("indoor_evening")
    a = process(rgb_image, load_theme("bright_airy"), condition, 1.0, 0)
    b = process(rgb_image, load_theme("dark_moody"), condition, 1.0, 0)
    assert np.abs(a - b).mean() > 0.05             # opposite looks: clearly different


def test_lut_theme_runs(rgb_image):
    out = process(rgb_image, load_theme("punch_overlay"),
                  get_condition("indoor_evening"), 1.0, 3)
    assert out.shape == rgb_image.shape
    assert not np.isnan(out).any()


def test_resolve_theme_from_inline_dict(rgb_image):
    cfg = resolve_theme({"exposure": {"stops": 0.5}})
    out = process(rgb_image, cfg, {}, 1.0, 0)
    assert out.shape == rgb_image.shape
