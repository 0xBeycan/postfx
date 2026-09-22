"""Typed enums for the public API — use `Theme.Signature.PORTRA_400` /
`Condition.NEON_NIGHT` instead of bare strings, with IDE autocomplete and
typo-checking.

`Theme` is a *namespace* grouping the built-in looks by category — one nested
`StrEnum` per shipped `themes/` subdirectory:

    Theme.Signature.PORTRA_400      # market-standard, reference-grounded looks
    Theme.Luts.PUNCH_OVERLAY        # LUT-backed looks (themes/luts/)
    Theme.Experimental.KODACHROME   # earlier / exploratory looks

Each member is still a `StrEnum`: a member *is* its string value, so it drops
straight into every string-accepting call — `process_file(theme=..., ...)`,
`load_theme(...)`, `get_condition(...)` — with no conversion. The `Theme`
namespace also behaves like the flat enum did for aggregate use:

    for t in Theme: ...             # iterates every member across all groups
    Theme("portra_400")             # round-trips a raw string back to a member
    "portra_400" in Theme           # membership test

`Condition` and `Luts` stay flat `StrEnum`s.

Members are hand-maintained; `tests/test_enums.py` asserts they stay in sync
with the YAML themes / `.cube` LUTs actually shipped, so any drift fails CI.
"""

import sys

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:  # Python 3.9 / 3.10 — minimal StrEnum backport (str-valued Enum).
    from enum import Enum

    class StrEnum(str, Enum):
        """A `str`-valued Enum: a member compares and formats as its value."""

        def __str__(self):
            return str(self.value)


class _ThemeNamespace(type):
    """Metaclass making `Theme` a namespace over its nested category enums.

    It restores the flat-enum ergonomics — iteration, string round-trip and
    membership — on top of the grouped `Theme.Signature.PORTRA_400` layout.
    """

    @property
    def _groups(cls):
        # Nested StrEnum classes, in definition order (== category order).
        return tuple(v for v in vars(cls).values()
                     if isinstance(v, type) and issubclass(v, StrEnum))

    def __iter__(cls):
        for group in cls._groups:
            yield from group

    def __call__(cls, value):
        """Round-trip a raw string (a member's value) back to that member."""
        for member in cls:
            if member == value:
                return member
        valid = ", ".join(m.value for m in cls)
        raise ValueError(f"{value!r} is not a valid Theme. Valid: {valid}")

    def __contains__(cls, value):
        return any(member == value for member in cls)


class Theme(metaclass=_ThemeNamespace):
    """Built-in theme names, grouped by category (the value passed to
    `--theme` / `theme=`). Iterate `Theme` for the flat set of all members.
    """

    class OurChoices(StrEnum):
        """House finishes: texture-only looks measured from published social
        stills — grain the way a platform-compressed phone photo carries it,
        colour untouched. Chain a Signature theme before one for a look."""

        FINE_GRAIN_LIGHT = "fine_grain_light"
        FINE_GRAIN_MEDIUM = "fine_grain_medium"
        FINE_GRAIN_HEAVY = "fine_grain_heavy"

    class Signature(StrEnum):
        """Market-standard, reference-grounded looks (primary set)."""

        PORTRA_400 = "portra_400"
        GOLD_200 = "gold_200"
        PRO_400H = "pro_400h"
        EKTAR_100 = "ektar_100"
        CINESTILL_800T = "cinestill_800t"
        SUPERIA_XTRA = "superia_xtra"
        KODACHROME_64 = "kodachrome_64"
        TRI_X_400 = "tri_x_400"
        CINEMATIC_TEAL_ORANGE = "cinematic_teal_orange"
        BLEACH_BYPASS = "bleach_bypass"
        BRIGHT_AIRY = "bright_airy"
        DARK_MOODY = "dark_moody"
        CLEAN_COMMERCIAL = "clean_commercial"
        GOLDEN_WARM = "golden_warm"
        MONO_NOIR = "mono_noir"

    class Luts(StrEnum):
        """LUT-backed looks — a `.cube` LUT is a selectable theme (themes/luts/)."""

        PUNCH_OVERLAY = "punch_overlay"

    class Experimental(StrEnum):
        """Earlier / exploratory looks."""

        CLEAN_EDITORIAL = "clean_editorial"
        WARM_PORTRA = "warm_portra"
        TEAL_ORANGE = "teal_orange"
        FADED_MATTE = "faded_matte"
        GOLDEN_HOUR = "golden_hour"
        NORDIC_COOL = "nordic_cool"
        PUNCHY_SOCIAL = "punchy_social"
        ANALOG_35MM = "analog_35mm"
        Y2K_DIGICAM = "y2k_digicam"
        SOFT_PASTEL = "soft_pastel"
        MOODY_DARK = "moody_dark"
        KODACHROME = "kodachrome"
        NEUTRAL_MINIMAL = "neutral_minimal"
        NEON_NIGHT = "neon_night"
        SUNBLEACHED = "sunbleached"


class Condition(StrEnum):
    """Shooting-condition names (the value passed to `--condition` / `condition=`).

    Ordered by increasing texture intensity. `NEUTRAL` is the identity default.
    """

    NEUTRAL = "neutral"
    DAY_OUTDOOR = "day_outdoor"
    OVERCAST = "overcast"
    INDOOR_EVENING = "indoor_evening"
    NEON_NIGHT = "neon_night"
    NIGHT_FLASH = "night_flash"


class Luts(StrEnum):
    """Bundled `.cube` 3D LUT names (referenced by a theme's `lut.file`)."""

    PUNCH_OVERLAY = "PunchOverlay"
