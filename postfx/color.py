"""Color-space conversions and white-balance (Bradford) matrices.

All functions are pure: numpy array in, new numpy array out. No side effects.
Images are float32, RGB channel order. Values may exceed [0,1] in linear space
(highlights) inside the pipeline; that is intentional.
"""

import numpy as np

# --- sRGB (D65) <-> XYZ ---------------------------------------------------
_XYZ_FROM_RGB = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
], dtype=np.float64)
_RGB_FROM_XYZ = np.linalg.inv(_XYZ_FROM_RGB)

# --- Bradford chromatic adaptation (XYZ <-> LMS cone space) ---------------
_BRADFORD = np.array([
    [0.8951000, 0.2664000, -0.1614000],
    [-0.7502000, 1.7135000, 0.0367000],
    [0.0389000, -0.0685000, 1.0296000],
], dtype=np.float64)
_BRADFORD_INV = np.linalg.inv(_BRADFORD)

# Rec.709 luminance weights — used for luma masks and neutral-gray preservation.
LUMA = np.array([0.2126729, 0.7151522, 0.0721750], dtype=np.float32)


def srgb_to_linear(x):
    """sRGB (display) -> linear light. Input [0,1] float, output float32."""
    x = np.asarray(x, dtype=np.float32)
    a = 0.055
    return np.where(
        x <= 0.04045,
        x / 12.92,
        np.power(np.clip((x + a) / (1.0 + a), 0.0, None), 2.4),
    ).astype(np.float32)


def linear_to_srgb(x):
    """Linear light -> sRGB (display). Clamps negatives, output float32."""
    x = np.clip(np.asarray(x, dtype=np.float32), 0.0, None)
    a = 0.055
    return np.where(
        x <= 0.0031308,
        x * 12.92,
        (1.0 + a) * np.power(x, 1.0 / 2.4) - a,
    ).astype(np.float32)


def apply_matrix(img, m):
    """Apply a 3x3 matrix per pixel to an HxWx3 image (out = M . pixel)."""
    m = np.asarray(m, dtype=np.float32)
    return (img @ m.T).astype(np.float32)


def white_balance_matrix(temp, tint):
    """Bradford-based white-balance matrix (linear sRGB -> linear sRGB).

    temp > 0 = warmer (red up, blue down), temp < 0 = cooler.
    tint > 0 = magenta direction, tint < 0 = green direction.
    Gains are applied in LMS cone space, then the matrix is normalized so that
    neutral-gray luminance is preserved (white balance must not change exposure).
    """
    g_l = 1.0 + 0.20 * float(temp)   # long-wavelength (red) cone
    g_s = 1.0 - 0.20 * float(temp)   # short-wavelength (blue) cone
    g_m = 1.0 - 0.15 * float(tint)   # medium-wavelength (green) cone
    gains = np.diag([g_l, g_m, g_s]).astype(np.float64)

    adapt_xyz = _BRADFORD_INV @ gains @ _BRADFORD
    a = _RGB_FROM_XYZ @ adapt_xyz @ _XYZ_FROM_RGB

    # Keep the luminance of neutral gray (1,1,1) constant.
    white = a @ np.ones(3)
    luma = np.array([0.2126729, 0.7151522, 0.0721750])
    a = a / float(luma @ white)
    return a.astype(np.float32)
