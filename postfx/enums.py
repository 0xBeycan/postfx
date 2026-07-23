"""Typed enums for the public API — use `Theme.PORTRA_400` / `Condition.NEON_NIGHT`
instead of bare strings, with IDE autocomplete and typo-checking.

Each is a `StrEnum`: a member *is* its string value, so it drops straight into
every string-accepting call — `process_file(theme=Theme.PORTRA_400, ...)`,
`load_theme(Theme.PORTRA_400)`, `get_condition(Condition.NEUTRAL)` — with no
conversion. `Theme("portra_400")` round-trips a raw string back to a member.

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


class Theme(StrEnum):
    """Built-in theme names (the value passed to `--theme` / `theme=`)."""

    # signature — market-standard, reference-grounded looks (primary set)
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
    # luts — a LUT is a selectable theme
    PUNCH_OVERLAY = "punch_overlay"
    # experimental — earlier / exploratory looks
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
