"""Atomic post-process operations.

Rule: every op is a pure function — (input array + parameters) -> new array,
no side effects. Input/output are float32, HxWx3, RGB. The color space each op
expects (linear or sRGB) is noted in its docstring; the pipeline manages order.
"""

import functools

import numpy as np

from .color import LUMA


def _gaussian(img, sigma):
    """Gaussian blur with ksize derived from sigma (border: reflect)."""
    import cv2
    if sigma <= 0:
        return img
    return cv2.GaussianBlur(
        img, (0, 0), sigmaX=float(sigma), sigmaY=float(sigma),
        borderType=cv2.BORDER_REFLECT,
    )


# --- Tonal (linear space) -------------------------------------------------

def exposure(lin, stops):
    """Exposure in stops. Multiplicative in linear space."""
    if stops == 0:
        return lin
    return (lin * (2.0 ** float(stops))).astype(np.float32)


def highlight_rolloff(lin, knee=0.7, strength=0.0):
    """Soft-knee highlight compression (breaks clipped plastic highlights).

    Values above the knee are compressed with a rational curve toward the
    asymptote knee + 1/strength. Works in linear space; strength=0 => off.
    """
    if strength <= 0:
        return lin
    e = lin - knee
    comp = knee + e / (1.0 + float(strength) * np.clip(e, 0.0, None))
    return np.where(lin > knee, comp, lin).astype(np.float32)


def lift_gamma_gain(x, lift, gamma, gain):
    """Per-channel Lift/Gamma/Gain (ASC-CDL: out = (x*gain + lift) ^ (1/gamma)).

    gain = slope (affects highlights), lift = offset (affects shadows),
    gamma = power (affects midtones); each is a 3-element [R,G,B].
    """
    gain = np.asarray(gain, dtype=np.float32)
    lift = np.asarray(lift, dtype=np.float32)
    gamma = np.asarray(gamma, dtype=np.float32)
    out = np.clip(x * gain + lift, 0.0, None)
    # Skip the power at neutral gamma: np.power(_, 1.0) is not bit-exact on
    # every numpy build, so applying it would break the neutral-identity
    # invariant and byte-for-byte determinism (seen as a 3.14 x86 CI failure,
    # exact on macOS). Non-neutral gamma is unchanged.
    if np.all(gamma == 1.0):
        return out.astype(np.float32)
    return np.power(out, 1.0 / gamma).astype(np.float32)


def split_toning(x, shadow, highlight, strength=0.0):
    """Luma-masked split tone: separate RGB shift for shadows and highlights.

    shadow/highlight = small signed [R,G,B] offset vectors. The shadow mask is
    (1-luma)^2 and the highlight mask is luma^2.
    """
    if strength <= 0:
        return x
    shadow = np.asarray(shadow, dtype=np.float32)
    highlight = np.asarray(highlight, dtype=np.float32)
    luma = np.clip(x @ LUMA, 0.0, 1.0)[..., None]
    s_w = (1.0 - luma) ** 2
    h_w = luma ** 2
    out = x + float(strength) * (s_w * shadow + h_w * highlight)
    return out.astype(np.float32)


def tone_curve(x, strength=0.0, pivot=0.45):
    """Adjustable S-curve (tanh-based). Fixes 0->0 and 1->1; contrast around the
    pivot. Higher strength steepens the curve; gentle shoulder for x>1.
    """
    if strength <= 0:
        return x
    a = float(strength) * 4.0
    t0 = np.tanh(-a * pivot)
    t1 = np.tanh(a * (1.0 - pivot))
    num = np.tanh(a * (x - pivot)) - t0
    return np.clip(num / (t1 - t0), 0.0, None).astype(np.float32)


def vibrance_saturation(x, vibrance=0.0, saturation=1.0, skin_protect=0.5):
    """Vibrance + Saturation (separate). Saturation scales uniformly; vibrance
    lifts low-saturation pixels more and protects skin tones.
    """
    if saturation == 1.0 and vibrance == 0.0:
        return x
    luma = (x @ LUMA)[..., None]
    if saturation != 1.0:
        x = luma + float(saturation) * (x - luma)
    if vibrance != 0.0:
        xc = np.clip(x, 0.0, 1.0)
        mx = xc.max(axis=2)
        mn = xc.min(axis=2)
        sat = (mx - mn) / (mx + 1e-6)          # HSV-like saturation 0..1
        weight = 1.0 - sat                     # low sat => larger weight
        if skin_protect > 0:
            r, g, b = xc[..., 0], xc[..., 1], xc[..., 2]
            skin = ((r > g) & (g > b) & (r - b > 0.02)).astype(np.float32)
            weight = weight * (1.0 - float(skin_protect) * skin)
        x = luma + (1.0 + float(vibrance) * weight[..., None]) * (x - luma)
    return x.astype(np.float32)


def halation(lin, threshold=0.7, radius_frac=0.01, tint=(1.0, 0.6, 0.4),
             strength=0.0):
    """Halation / bloom — in LINEAR space. Highlight threshold -> gaussian blur
    -> red-shifted tint -> screen blend. Blur radius scales with image size
    (radius_frac * min(H,W)), so it looks resolution-independent.
    """
    if strength <= 0:
        return lin
    h, w = lin.shape[:2]
    sigma = max(1.0, float(radius_frac) * min(h, w))
    luma = lin @ LUMA
    mask = np.clip((luma - threshold) / max(1e-6, 1.0 - threshold), 0.0, 1.0)
    src = np.clip(lin, 0.0, 1.0) * mask[..., None]
    glow = _gaussian(src, sigma) * np.asarray(tint, dtype=np.float32) * float(strength)
    base = lin
    out = base + glow - np.clip(base, 0.0, 1.0) * glow   # screen, preserves highlights
    return np.clip(out, 0.0, None).astype(np.float32)


# --- Geometry / lens (sRGB space) ----------------------------------------

def _center_grid(h, w):
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    ys, xs = np.mgrid[0:h, 0:w]
    return xs.astype(np.float32), ys.astype(np.float32), cx, cy


def barrel_distortion(img, k=0.0):
    """Barrel (k<0) / pincushion (k>0) distortion. Radius normalized by the
    half-diagonal; size preserved, edges filled by reflection.
    """
    import cv2
    if k == 0:
        return img
    h, w = img.shape[:2]
    xs, ys, cx, cy = _center_grid(h, w)
    norm = np.hypot(cx, cy)
    dx, dy = (xs - cx) / norm, (ys - cy) / norm
    factor = 1.0 + float(k) * (dx * dx + dy * dy)
    map_x = (cx + (xs - cx) * factor).astype(np.float32)
    map_y = (cy + (ys - cy) * factor).astype(np.float32)
    return cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REFLECT)


def chromatic_aberration(img, amount=0.0):
    """Lateral CA — magnify the R channel from center, shrink the B channel.
    Color fringing increases toward the edges. amount is typically 0.001-0.004.
    """
    import cv2
    if amount == 0:
        return img
    h, w = img.shape[:2]
    xs, ys, cx, cy = _center_grid(h, w)
    dx, dy = xs - cx, ys - cy
    out = img.copy()
    for ch, s in ((0, 1.0 + float(amount)), (2, 1.0 - float(amount))):
        map_x = (cx + dx / s).astype(np.float32)
        map_y = (cy + dy / s).astype(np.float32)
        out[..., ch] = cv2.remap(img[..., ch], map_x, map_y, cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_REFLECT)
    return out


def vignette(img, strength=0.0, feather=0.5, roundness=1.0):
    """Radial vignette. feather: normalized radius (0..1) where darkening starts,
    strength: darkening amount at the edge. smoothstep transition.
    """
    if strength <= 0:
        return img
    h, w = img.shape[:2]
    xs, ys, cx, cy = _center_grid(h, w)
    norm = np.hypot(cx, cy)
    r = np.hypot((xs - cx) * roundness, ys - cy) / norm
    t = np.clip((r - feather) / max(1e-6, 1.0 - feather), 0.0, 1.0)
    falloff = t * t * (3.0 - 2.0 * t)
    vig = 1.0 - float(strength) * falloff
    return (img * vig[..., None]).astype(np.float32)


def black_point_lift(img, lift=0.0):
    """Lift the black point (matte/faded film). Maps [0,1] -> [lift,1].
    lift can be a scalar or an [R,G,B] for tinted blacks.
    """
    lift = np.asarray(lift, dtype=np.float32)
    if np.all(lift == 0):
        return img
    return (lift + (1.0 - lift) * img).astype(np.float32)


# --- Texture (sRGB space) -------------------------------------------------

def clarity(img, amount=0.0, radius_frac=0.03):
    """Local contrast (wide-radius unsharp), applied to luma detail — avoids
    color shift. amount can be negative (softening/soft focus).
    """
    if amount == 0:
        return img
    h, w = img.shape[:2]
    sigma = max(1.0, float(radius_frac) * min(h, w))
    luma = img @ LUMA
    detail = (luma - _gaussian(luma, sigma))[..., None]
    return np.clip(img + float(amount) * detail, 0.0, 1.0).astype(np.float32)


GRAIN_REF = 1024.0  # reference long edge at which grain 'size' is measured in px


def grain(img, luma_amount=0.0, chroma_amount=0.0, size=1.5, floor=0.1, seed=0):
    """Luminance-weighted film grain. Strongest in midtones, weaker in
    highlights and deep shadows. Luma noise (monochrome) and chroma noise
    (colored) are separate.

    Resolution-INDEPENDENT appearance: grain is generated at a low resolution
    that depends only on size and GRAIN_REF, then upscaled to full res. So
    'size' yields the same relative grain regardless of the image's pixel count
    ('size' px at the GRAIN_REF reference). Below 1.0 the grain gets finer than
    the reference pixel grid; once it would be finer than the image's own
    pixels (size <= GRAIN_REF / long edge) it is plain per-pixel noise — the
    sensor-noise look that disappears when the image is viewed small.
    seed makes it deterministic.
    """
    import cv2
    if luma_amount <= 0 and chroma_amount <= 0:
        return img
    h, w = img.shape[:2]
    rng = np.random.default_rng(int(seed))
    long_edge = max(h, w)
    # Generation size along the long edge = GRAIN_REF/size (resolution-independent).
    scale = min(1.0, (GRAIN_REF / max(0.25, size)) / long_edge)
    lh = max(2, int(round(h * scale)))
    lw = max(2, int(round(w * scale)))

    luma_n = cv2.resize(
        rng.standard_normal((lh, lw)).astype(np.float32), (w, h),
        interpolation=cv2.INTER_CUBIC)
    chroma_n = cv2.resize(
        rng.standard_normal((lh, lw, 3)).astype(np.float32), (w, h),
        interpolation=cv2.INTER_CUBIC)

    lum = np.clip(img @ LUMA, 0.0, 1.0)
    mid = 1.0 - (2.0 * lum - 1.0) ** 2               # 0 at black/white, 1 at midtone
    mid = float(floor) + (1.0 - float(floor)) * mid

    out = img + (float(luma_amount) * luma_n * mid)[..., None]
    out = out + float(chroma_amount) * chroma_n * mid[..., None]
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def sharpen(img, amount=0.0, radius_frac=0.0015, halo=0.0):
    """Unsharp mask, narrow radius. Optional slight halo (wider overshoot)."""
    if amount <= 0 and halo <= 0:
        return img
    h, w = img.shape[:2]
    sigma = max(0.5, float(radius_frac) * min(h, w))
    out = img + float(amount) * (img - _gaussian(img, sigma))
    if halo > 0:
        out = out + float(halo) * (img - _gaussian(img, sigma * 3.0))
    return np.clip(out, 0.0, 1.0).astype(np.float32)


# --- Optional creative LUT (.cube), display-referred (sRGB space) ---------

@functools.lru_cache(maxsize=16)
def load_cube_lut(path):
    """Parse a 3D .cube LUT into {size, min, max, table[b,g,r,3]}. Cached by path.

    Only 3D LUTs are supported (the common creative-look format). This lets a
    theme drop in a user-supplied .cube (e.g. a purchased DaVinci/Photoshop
    look) without bundling any copyrighted files in the package.
    """
    size = None
    domain_min = [0.0, 0.0, 0.0]
    domain_max = [1.0, 1.0, 1.0]
    data = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            u = s.upper()
            if u.startswith("LUT_3D_SIZE"):
                size = int(s.split()[-1])
            elif u.startswith("LUT_1D_SIZE"):
                raise ValueError("1D LUTs are not supported (need a 3D .cube).")
            elif u.startswith("DOMAIN_MIN"):
                domain_min = [float(x) for x in s.split()[1:4]]
            elif u.startswith("DOMAIN_MAX"):
                domain_max = [float(x) for x in s.split()[1:4]]
            elif u.startswith("TITLE"):
                continue
            else:
                parts = s.split()
                if len(parts) == 3:
                    try:
                        data.append([float(parts[0]), float(parts[1]), float(parts[2])])
                    except ValueError:
                        continue
    if size is None:
        raise ValueError(f"{path}: LUT_3D_SIZE not found.")
    arr = np.asarray(data, dtype=np.float32)
    if arr.shape[0] != size ** 3:
        raise ValueError(f"{path}: expected {size**3} entries, got {arr.shape[0]}.")
    # .cube stores red varying fastest -> reshape gives table[b, g, r].
    table = arr.reshape(size, size, size, 3)
    return {"size": size,
            "min": np.asarray(domain_min, np.float32),
            "max": np.asarray(domain_max, np.float32),
            "table": table}


def apply_lut(img, lut, intensity=1.0):
    """Apply a parsed 3D LUT (from load_cube_lut) with trilinear interpolation.
    intensity blends between original (0) and full LUT (1). sRGB [0,1] space.
    """
    if lut is None or intensity <= 0:
        return img
    n = lut["size"]
    table = lut["table"]
    x = np.clip((img - lut["min"]) / np.maximum(lut["max"] - lut["min"], 1e-6),
                0.0, 1.0) * (n - 1)
    x0 = np.floor(x).astype(np.int32)
    x1 = np.minimum(x0 + 1, n - 1)
    f = (x - x0).astype(np.float32)
    r0, g0, b0 = x0[..., 0], x0[..., 1], x0[..., 2]
    r1, g1, b1 = x1[..., 0], x1[..., 1], x1[..., 2]
    fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]

    c000, c100 = table[b0, g0, r0], table[b0, g0, r1]
    c010, c110 = table[b0, g1, r0], table[b0, g1, r1]
    c001, c101 = table[b1, g0, r0], table[b1, g0, r1]
    c011, c111 = table[b1, g1, r0], table[b1, g1, r1]
    c00 = c000 * (1 - fr) + c100 * fr
    c10 = c010 * (1 - fr) + c110 * fr
    c01 = c001 * (1 - fr) + c101 * fr
    c11 = c011 * (1 - fr) + c111 * fr
    c0 = c00 * (1 - fg) + c10 * fg
    c1 = c01 * (1 - fg) + c11 * fg
    out = c0 * (1 - fb) + c1 * fb

    if intensity < 1.0:
        out = img * (1.0 - intensity) + out * intensity
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def jpeg_cycle(img_u8, quality=95, cycles=1):
    """JPEG encode/decode loop — adds compression character. Operates on uint8
    BGR (cv2). cycles=0 => no-op.
    """
    import cv2
    if cycles <= 0:
        return img_u8
    out = img_u8
    for _ in range(int(cycles)):
        ok, enc = cv2.imencode('.jpg', out,
                               [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
        if not ok:
            break
        out = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    return out
