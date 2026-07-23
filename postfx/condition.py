"""Shooting-condition profiles — a second axis, independent of the theme.

A theme decides the *look* (color grading). A condition decides *how strongly*
the capture/optical artifacts read — grain, chroma noise and halation — for the
situation a shot was taken in. Conditions apply as MULTIPLIERS on top of the
theme's own values, so a single theme stays consistent yet condition-aware
across daylight, overcast, indoor, neon and flash situations.

Like themes, conditions are decoupled from code: each is a YAML file under
conditions/ carrying grain / chroma_noise / halation multipliers. A missing key
fills from CONDITION_DEFAULTS (1.0 = leave the theme's value unchanged); an
unknown key raises (this catches typos). The second header comment line is the
condition's description.
"""

import os

import yaml

CONDITIONS_DIR = os.path.join(os.path.dirname(__file__), "conditions")

# Neutral multipliers. 1.0 = apply the theme's value unchanged (no scaling).
CONDITION_DEFAULTS = {"grain": 1.0, "chroma_noise": 1.0, "halation": 1.0}

# The identity condition (all multipliers 1.0). Used when none is given.
DEFAULT_CONDITION = "neutral"

# Meta keys are not multipliers; they must not fail validation.
_META_KEYS = {"name", "description"}


def validate(raw, source="<condition>"):
    """Validate a raw condition dict. Raises ValueError on unknown keys."""
    if not isinstance(raw, dict):
        raise ValueError(f"{source}: a condition must be a mapping.")
    for key in raw:
        if key in _META_KEYS or key in CONDITION_DEFAULTS:
            continue
        raise ValueError(
            f"{source}: unknown key {key!r}. "
            f"Valid keys: {', '.join(sorted(CONDITION_DEFAULTS))}")
    return True


def _stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def _name(path):
    """User-facing name: the stem without any leading 'NN_' ordering prefix."""
    head, sep, tail = _stem(path).partition("_")
    return tail if sep and head.isdigit() else _stem(path)


def _read_header(path):
    """Collect the leading '# ...' comment lines as the condition's description."""
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


def list_condition_files(conditions_dir=CONDITIONS_DIR):
    """Return condition .yaml files, sorted by filename (NN_ prefix orders them
    by increasing texture intensity)."""
    files = [os.path.join(conditions_dir, f)
             for f in os.listdir(conditions_dir)
             if f.endswith((".yaml", ".yml"))]
    return sorted(files, key=_stem)


def _resolve_path(name_or_path, conditions_dir=CONDITIONS_DIR):
    if os.path.isfile(name_or_path):
        return name_or_path
    candidates = list_condition_files(conditions_dir)
    for path in candidates:
        # match 'day_outdoor', '02_day_outdoor', or the full file name
        if name_or_path in (_name(path), _stem(path), os.path.basename(path)):
            return path
    raise FileNotFoundError(
        f"Condition not found: {name_or_path!r}. Available: "
        f"{', '.join(_name(p) for p in candidates)}")


def load_condition(name_or_path, conditions_dir=CONDITIONS_DIR):
    """Load a condition by name (e.g. 'day_outdoor') or by path; return the
    grain/chroma_noise/halation multipliers merged over CONDITION_DEFAULTS,
    plus 'name' and 'description'.
    """
    path = _resolve_path(name_or_path, conditions_dir)
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    validate(raw, source=os.path.basename(path))
    cfg = dict(CONDITION_DEFAULTS)
    cfg.update({k: v for k, v in raw.items() if k not in _META_KEYS})
    cfg["name"] = raw.get("name", _name(path))
    header = _read_header(path)
    cfg["description"] = raw.get("description",
                                 header[1] if len(header) > 1 else "")
    return cfg


def get_condition(name=None):
    """Return just the {grain, chroma_noise, halation} multipliers for a
    condition by name. None => the default (neutral). Raises on an unknown name.
    This is the form the pipeline consumes.
    """
    cfg = load_condition(name if name is not None else DEFAULT_CONDITION)
    return {key: cfg[key] for key in CONDITION_DEFAULTS}


def list_conditions(conditions_dir=CONDITIONS_DIR):
    """List of (name, description) tuples — for the CLI 'list' command."""
    out = []
    for path in list_condition_files(conditions_dir):
        header = _read_header(path)
        desc = header[1] if len(header) > 1 else ""
        out.append((_name(path), desc))
    return out
