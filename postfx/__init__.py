"""postfx — theme-based image post-process / branding pipeline.

Pure Python (numpy, opencv, Pillow, PyYAML). Standalone and dependency-light.
Runs on CPU; no GPU required.

Quick use:
    from postfx import process_file
    process_file("in.png", "out.png", theme="portra_400", scene="day_outdoor")
"""

from . import color, imgio, ops
from .pipeline import process, resolve_theme
from .scenes import DEFAULT_SCENE, SCENES, get_scene
from .theme import (DEFAULT_CATEGORY, list_categories, list_luts, list_themes,
                    load_theme)

__version__ = "1.0.0"

__all__ = [
    "process", "process_file", "resolve_theme", "load_theme", "list_themes",
    "list_categories", "list_luts", "get_scene", "SCENES", "DEFAULT_SCENE",
    "DEFAULT_CATEGORY", "color", "ops", "imgio", "__version__",
]


def process_file(in_path, out_path, theme="portra_400",
                 scene=DEFAULT_SCENE, strength=1.0):
    """Process and save a single file. theme: name/path; scene: name.
    Convenience wrapper around load + process + save.
    """
    theme_cfg = resolve_theme(theme)
    scene_cfg = get_scene(scene) if isinstance(scene, str) else scene
    rgb, alpha = imgio.load_image(in_path)
    seed = imgio.seed_from_path(in_path)
    out = process(rgb, theme_cfg, scene_cfg, strength, seed)
    imgio.save_image(out_path, out, alpha,
                     jpeg_quality=theme_cfg["jpeg"]["quality"],
                     jpeg_cycles=theme_cfg["jpeg"]["cycles"])
    return out_path
