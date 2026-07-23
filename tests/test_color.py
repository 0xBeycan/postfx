import numpy as np

from postfx import color


def test_srgb_linear_roundtrip():
    x = np.linspace(0, 1, 4096, dtype=np.float32)
    rt = color.linear_to_srgb(color.srgb_to_linear(x))
    assert np.abs(rt - x).max() < 1e-5


def test_srgb_linear_endpoints():
    assert abs(float(color.srgb_to_linear(np.float32(0.0)))) < 1e-7
    assert abs(float(color.srgb_to_linear(np.float32(1.0))) - 1.0) < 1e-5


def test_linear_to_srgb_clamps_negative():
    out = color.linear_to_srgb(np.array([-0.5, 0.0, 0.5], np.float32))
    assert not np.isnan(out).any()
    assert out[0] == 0.0


def test_white_balance_preserves_neutral_luma():
    gray = np.array([0.4, 0.4, 0.4], np.float32)
    for temp, tint in [(0.5, 0.0), (-0.4, 0.1), (0.2, -0.15)]:
        m = color.white_balance_matrix(temp, tint)
        out = gray @ m.T
        assert abs(float(out @ color.LUMA) - float(gray @ color.LUMA)) < 1e-4


def test_white_balance_identity_at_zero():
    m = color.white_balance_matrix(0.0, 0.0)
    assert np.allclose(m, np.eye(3), atol=1e-5)


def test_white_balance_warm_shifts_red_up_blue_down():
    m = color.white_balance_matrix(0.5, 0.0)
    gray = np.array([0.5, 0.5, 0.5], np.float32)
    out = gray @ m.T
    assert out[0] > out[2]  # red > blue (warmer)
