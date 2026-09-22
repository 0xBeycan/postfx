"""Contact sheet generation — apply themes to one image in a labeled grid.

Used to let a client pick a theme. For speed it first downscales the source
(the grid is a preview, not the deliverable), applies each theme, arranges them
into a grid with name labels, and saves a single JPG. Defaults to the
'signature' category (the market-standard set).
"""

import math
import os

import numpy as np

from .condition import get_condition
from .pipeline import process
from .theme import list_theme_files, load_theme


def _fit_width(rgb, target_w):
    import cv2
    h, w = rgb.shape[:2]
    if w <= target_w:
        return rgb
    scale = target_w / float(w)
    return cv2.resize(rgb, (target_w, max(1, int(round(h * scale)))),
                      interpolation=cv2.INTER_AREA)


def _font(size):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def build_contact_sheet(rgb, out_path, category="signature", condition="neutral",
                        strength=1.0, seed=None, cols=5, thumb_w=460, pad=14,
                        label_h=34, themes_dir=None):
    """Apply every theme in `category` to `rgb` and save a labeled grid.

    category: theme category ('signature', 'experimental', or 'all').
    """
    from PIL import Image, ImageDraw
    condition_cfg = get_condition(condition)
    if seed is None:
        seed = 12345  # fixed for the sheet: a fair comparison across themes

    kwargs = {"category": category}
    if themes_dir:
        kwargs["themes_dir"] = themes_dir
    theme_files = list_theme_files(**kwargs)

    src = _fit_width(rgb, thumb_w)
    th, tw = src.shape[:2]

    rows = math.ceil(len(theme_files) / cols)
    cell_w = tw + pad
    cell_h = th + label_h + pad
    sheet_w = cols * cell_w + pad
    sheet_h = rows * cell_h + pad

    canvas = Image.new("RGB", (sheet_w, sheet_h), (18, 18, 20))
    draw = ImageDraw.Draw(canvas)
    font = _font(20)

    for idx, path in enumerate(theme_files):
        theme = load_theme(path)
        out = process(src, theme, condition_cfg, strength, seed)
        u8 = np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8)
        tile = Image.fromarray(u8)

        r, c = divmod(idx, cols)
        x = pad + c * cell_w
        y = pad + r * cell_h
        canvas.paste(tile, (x, y))

        stem = os.path.splitext(os.path.basename(path))[0]
        label = stem.replace("_", " ")
        draw.text((x + 2, y + th + 7), label, fill=(235, 235, 235), font=font)

    canvas.save(out_path, quality=92)
    return out_path
