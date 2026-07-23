"""Scene profiles — a second axis, independent of the theme.

They modulate grain, chroma noise and halation as MULTIPLIERS on top of the
theme's own values. This keeps a single theme consistent yet condition-aware
across different shooting situations.
"""

SCENES = {
    # daytime outdoor: clean, minimal grain, no chroma noise, light bloom
    "day_outdoor":    {"grain": 0.15, "chroma_noise": 0.0, "halation": 0.7},
    # indoor evening: reference / neutral profile (default)
    "indoor_evening": {"grain": 1.0,  "chroma_noise": 0.5, "halation": 1.0},
    # night flash: heavy grain, strong chroma noise, boosted halation
    "night_flash":    {"grain": 2.2,  "chroma_noise": 1.5, "halation": 1.4},
}

DEFAULT_SCENE = "indoor_evening"


def get_scene(name):
    """Return a dict of scene multipliers by name. Raises on unknown name."""
    if name is None:
        name = DEFAULT_SCENE
    if name not in SCENES:
        raise KeyError(
            f"Unknown scene: {name!r}. Options: {', '.join(SCENES)}")
    return dict(SCENES[name])
