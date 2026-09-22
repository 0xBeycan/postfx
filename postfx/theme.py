"""Theme YAML loading, validation and defaults merge.

Themes are fully decoupled from code: each theme is a YAML file carrying op
parameters. Missing keys are filled from DEFAULTS (no-op / neutral), so even a
partial theme is valid. An unknown key raises (this catches typos).

Themes are organized into category subdirectories under themes/:
  themes/signature/     market-standard, reference-grounded looks (primary)
  themes/experimental/  earlier / exploratory looks
Theme names are unique across categories, so resolution by name works globally.
"""

import copy
import os


THEMES_DIR = os.path.join(os.path.dirname(__file__), "themes")
DEFAULT_CATEGORY = "signature"

# Preferred display/order of categories (unknown categories sort last).
_CATEGORY_ORDER = {"signature": 0, "luts": 1, "experimental": 2}

# Neutral / no-op defaults. If a theme omits a key, the value here applies and
# that op leaves the image unchanged.
DEFAULTS = {
    "white_balance": {"temp": 0.0, "tint": 0.0},
    "exposure": {"stops": 0.0},
    "highlight_rolloff": {"knee": 0.7, "strength": 0.0},
    "lift_gamma_gain": {
        "lift": [0.0, 0.0, 0.0],
        "gamma": [1.0, 1.0, 1.0],
        "gain": [1.0, 1.0, 1.0],
    },
    "split_toning": {
        "shadow": [0.0, 0.0, 0.0],
        "highlight": [0.0, 0.0, 0.0],
        "strength": 0.0,
    },
    "tone_curve": {"strength": 0.0, "pivot": 0.45},
    "vibrance": {"vibrance": 0.0, "saturation": 1.0, "skin_protect": 0.5},
    "halation": {
        "threshold": 0.7, "radius_frac": 0.01,
        "tint": [1.0, 0.6, 0.4], "strength": 0.0,
    },
    "distortion": {"k": 0.0},
    "chromatic_aberration": {"amount": 0.0},
    "vignette": {"strength": 0.0, "feather": 0.5, "roundness": 1.0},
    "black_point": {"lift": 0.0},
    "clarity": {"amount": 0.0, "radius_frac": 0.03},
    "grain": {"luma": 0.0, "chroma": 0.0, "size": 1.5, "floor": 0.1},
    "sharpen": {"amount": 0.0, "radius_frac": 0.0015, "halo": 0.0},
    "jpeg": {"quality": 95, "cycles": 0},
    # Optional creative LUT (.cube). Empty file => skipped. Path is resolved
    # relative to the theme's own directory if not absolute.
    "lut": {"file": "", "intensity": 1.0},
}

# Meta keys are not ops; they must not fail validation.
_META_KEYS = {"name", "description"}


def _deep_merge(base, override):
    out = copy.deepcopy(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def validate(raw, source="<theme>"):
    """Validate a raw theme dict. Raises ValueError on unknown op keys."""
    if not isinstance(raw, dict):
        raise ValueError(f"{source}: a theme must be a mapping.")
    for key in raw:
        if key in _META_KEYS or key in DEFAULTS:
            continue
        raise ValueError(
            f"{source}: unknown key {key!r}. "
            f"Valid ops: {', '.join(sorted(DEFAULTS))}")
    for key, value in raw.items():
        if key in DEFAULTS and not isinstance(value, dict):
            raise ValueError(f"{source}: {key!r} must be a mapping.")
    return True


def _read_header(path):
    """Collect the leading '# ...' comment lines as the theme's description."""
    lines = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped.startswith("#"):
                lines.append(stripped.lstrip("#").strip())
            elif stripped == "":
                continue
            else:
                break
    return lines


def _stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def _category_of(path):
    parent = os.path.basename(os.path.dirname(path))
    return parent if parent != "themes" else ""


def _sort_key(path):
    return (_CATEGORY_ORDER.get(_category_of(path), 99), _stem(path))


def load_theme(name_or_path):
    """Load a theme by name (e.g. 'portra_400' or '01_portra_400') or by path;
    return the full config merged with DEFAULTS.
    """
    import yaml

    path = _resolve_path(name_or_path)
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    validate(raw, source=os.path.basename(path))
    cfg = _deep_merge(DEFAULTS, {k: v for k, v in raw.items()
                                 if k not in _META_KEYS})
    cfg["name"] = raw.get("name", _stem(path))
    header = _read_header(path)
    cfg["description"] = raw.get("description",
                                 header[1] if len(header) > 1 else "")
    cfg["category"] = _category_of(path)
    cfg["_header"] = header
    cfg["_dir"] = os.path.dirname(os.path.abspath(path))
    _resolve_lut_path(cfg)
    return cfg


def _resolve_lut_path(cfg):
    """Make the theme's LUT file absolute (relative to the theme dir) and verify
    it exists. Empty file => no LUT. Fails fast on a missing referenced file.
    """
    lut_file = cfg.get("lut", {}).get("file", "")
    if not lut_file:
        return
    if not os.path.isabs(lut_file):
        lut_file = os.path.join(cfg["_dir"], lut_file)
    if not os.path.isfile(lut_file):
        raise FileNotFoundError(
            f"{cfg['name']}: LUT file not found: {cfg['lut']['file']!r}")
    cfg["lut"]["file"] = lut_file


def _resolve_path(name_or_path):
    if os.path.isfile(name_or_path):
        return name_or_path
    candidates = list_theme_files()
    target = name_or_path
    for path in candidates:
        stem = _stem(path)
        # match '01_portra_400', 'portra_400', or the full file name
        if target in (stem, stem.split("_", 1)[-1], os.path.basename(path)):
            return path
    raise FileNotFoundError(
        f"Theme not found: {name_or_path!r}. Available: "
        f"{', '.join(_stem(p) for p in candidates)}")


def list_categories(themes_dir=THEMES_DIR):
    """Return category subdirectory names that contain themes, ordered."""
    cats = []
    for name in os.listdir(themes_dir):
        d = os.path.join(themes_dir, name)
        if os.path.isdir(d) and any(f.endswith((".yaml", ".yml"))
                                    for f in os.listdir(d)):
            cats.append(name)
    return sorted(cats, key=lambda c: (_CATEGORY_ORDER.get(c, 99), c))


def list_theme_files(category=None, themes_dir=THEMES_DIR):
    """Return theme .yaml files. category=None/'all' => every category (ordered
    signature first); otherwise only that category's files.
    """
    if category and category != "all":
        d = os.path.join(themes_dir, category)
        if not os.path.isdir(d):
            raise FileNotFoundError(
                f"Unknown category: {category!r}. Available: "
                f"{', '.join(list_categories(themes_dir))}")
        files = [os.path.join(d, f) for f in os.listdir(d)
                 if f.endswith((".yaml", ".yml"))]
    else:
        files = []
        for root, _dirs, names in os.walk(themes_dir):
            for f in names:
                if f.endswith((".yaml", ".yml")):
                    files.append(os.path.join(root, f))
    return sorted(files, key=_sort_key)


def list_themes(category=None, themes_dir=THEMES_DIR):
    """List of (stem, description, category) tuples — for CLI 'list' and sheet."""
    out = []
    for path in list_theme_files(category, themes_dir):
        header = _read_header(path)
        desc = header[1] if len(header) > 1 else ""
        out.append((_stem(path), desc, _category_of(path)))
    return out


def list_luts(themes_dir=THEMES_DIR):
    """List bundled LUT cube files: [(name, path)], sorted by name.

    Users can also supply their own .cube via a theme's `lut.file`, so the
    bundled set is not the only source of LUTs.
    """
    out = []
    for root, _dirs, names in os.walk(themes_dir):
        for f in names:
            if f.lower().endswith(".cube"):
                out.append((os.path.splitext(f)[0], os.path.join(root, f)))
    return sorted(out, key=lambda t: t[0])
