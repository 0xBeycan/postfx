"""postfx — theme-based image post-processing & film-emulation pipeline.

Pure Python (numpy, opencv, Pillow, PyYAML). Standalone and dependency-light.
Runs on CPU; no GPU required.

Quick use:
    from postfx import process_file, Theme, Condition
    process_file("in.png", "out.png",
                 theme=Theme.PORTRA_400, condition=Condition.DAY_OUTDOOR)
"""

from . import color, imgio, ops
from .condition import (DEFAULT_CONDITION, get_condition, list_conditions,
                        load_condition)
from .enums import Condition, Luts, Theme
from .pipeline import process, resolve_theme
from .theme import (DEFAULT_CATEGORY, list_categories, list_luts, list_themes,
                    load_theme)

__version__ = "1.0.0"

__all__ = [
    "process", "process_file", "resolve_theme", "load_theme", "list_themes",
    "list_categories", "list_luts", "get_condition", "load_condition",
    "list_conditions", "DEFAULT_CONDITION", "DEFAULT_CATEGORY",
    "Theme", "Condition", "Luts",
    "color", "ops", "imgio", "__version__",
]


def process_file(in_path, out_path, theme=Theme.PORTRA_400,
                 condition=Condition.NEUTRAL, strength=1.0):
    """Process and save a single file. theme: name/path/Theme; condition:
    name/Condition. Convenience wrapper around load + process + save.
    """
    theme_cfg = resolve_theme(theme)
    condition_cfg = (get_condition(condition) if isinstance(condition, str)
                     else condition)
    rgb, alpha = imgio.load_image(in_path)
    seed = imgio.seed_from_path(in_path)
    out = process(rgb, theme_cfg, condition_cfg, strength, seed)
    imgio.save_image(out_path, out, alpha,
                     jpeg_quality=theme_cfg["jpeg"]["quality"],
                     jpeg_cycles=theme_cfg["jpeg"]["cycles"])
    return out_path
