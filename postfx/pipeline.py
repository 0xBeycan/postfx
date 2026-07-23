"""Pipeline orchestration — the processing order is fixed and critical here.

process(): sRGB float [0,1] in, processed sRGB float [0,1] out. The order must
not change (halation must be in linear space, grain in sRGB, etc.).
"""

import numpy as np

from . import color, ops
from .theme import DEFAULTS, load_theme


def process(img, theme, condition=None, strength=1.0, seed=0):
    """Apply a theme + condition + global strength to a single image.

    img      : float32 [0,1] sRGB, HxWx3
    theme    : theme dict merged with DEFAULTS (output of theme.load_theme)
    condition: {'grain','chroma_noise','halation'} multipliers, or None
    strength : 0=original, 1=full theme, 1.5=over (linear blend/extrapolate)
    seed     : integer for grain determinism
    """
    condition = condition or {}
    grain_mul = condition.get("grain", 1.0)
    chroma_mul = condition.get("chroma_noise", 1.0)
    hal_mul = condition.get("halation", 1.0)

    original = img
    t = theme

    # 1. sRGB -> linear
    lin = color.srgb_to_linear(img)

    # 2. White balance (Bradford)
    wb = t["white_balance"]
    lin = color.apply_matrix(lin, color.white_balance_matrix(wb["temp"], wb["tint"]))

    # 3. Exposure
    lin = ops.exposure(lin, t["exposure"]["stops"])

    # 4. Highlight rolloff
    hr = t["highlight_rolloff"]
    lin = ops.highlight_rolloff(lin, hr["knee"], hr["strength"])

    # 5. Lift / Gamma / Gain
    lgg = t["lift_gamma_gain"]
    lin = ops.lift_gamma_gain(lin, lgg["lift"], lgg["gamma"], lgg["gain"])

    # 6. Split toning
    st = t["split_toning"]
    lin = ops.split_toning(lin, st["shadow"], st["highlight"], st["strength"])

    # 7. Tone curve
    tc = t["tone_curve"]
    lin = ops.tone_curve(lin, tc["strength"], tc["pivot"])

    # 8. Vibrance + Saturation
    vs = t["vibrance"]
    lin = ops.vibrance_saturation(lin, vs["vibrance"], vs["saturation"],
                                  vs.get("skin_protect", 0.5))

    # 9. Halation / bloom (in linear space)
    ha = t["halation"]
    lin = ops.halation(lin, ha["threshold"], ha["radius_frac"], ha["tint"],
                       ha["strength"] * hal_mul)

    # 10. Linear -> sRGB
    srgb = color.linear_to_srgb(lin)

    # 10b. Optional creative LUT (.cube), display-referred. Skipped if unset.
    lut_cfg = t.get("lut", {})
    if lut_cfg.get("file"):
        srgb = ops.apply_lut(srgb, ops.load_cube_lut(lut_cfg["file"]),
                             lut_cfg.get("intensity", 1.0))

    # 11. Barrel/pincushion distortion
    srgb = ops.barrel_distortion(srgb, t["distortion"]["k"])

    # 12. Chromatic aberration
    srgb = ops.chromatic_aberration(srgb, t["chromatic_aberration"]["amount"])

    # 13. Vignette
    vg = t["vignette"]
    srgb = ops.vignette(srgb, vg["strength"], vg["feather"], vg.get("roundness", 1.0))

    # 14. Black point lift
    srgb = ops.black_point_lift(srgb, t["black_point"]["lift"])

    # 15. Clarity / local contrast
    cl = t["clarity"]
    srgb = ops.clarity(srgb, cl["amount"], cl["radius_frac"])

    # 16. Grain (luminance-weighted; condition multipliers here)
    gr = t["grain"]
    srgb = ops.grain(srgb, gr["luma"] * grain_mul, gr["chroma"] * chroma_mul,
                     gr["size"], gr.get("floor", 0.1), seed)

    # 17. Sharpening (+ optional halo)
    sh = t["sharpen"]
    srgb = ops.sharpen(srgb, sh["amount"], sh["radius_frac"], sh.get("halo", 0.0))

    srgb = np.clip(srgb, 0.0, 1.0)

    # Global strength: linearly blend/extrapolate the whole effect vs original.
    # (18. JPEG re-encode is applied in the save step.)
    if strength != 1.0:
        srgb = np.clip(original + float(strength) * (srgb - original), 0.0, 1.0)

    return srgb.astype(np.float32)


def resolve_theme(theme):
    """If theme is a name/path (str), load it; if already a dict, use as-is."""
    if isinstance(theme, str):
        return load_theme(theme)
    if isinstance(theme, dict) and "name" not in theme:
        # a raw/partial dict was given — fill with defaults
        from .theme import _deep_merge
        merged = _deep_merge(DEFAULTS, theme)
        merged.setdefault("name", "<inline>")
        merged.setdefault("description", "")
        return merged
    return theme
