from postfx import condition, theme
from postfx.enums import Condition, Luts, Theme
from postfx.theme import list_luts, list_theme_files


def test_theme_enum_matches_yaml_files():
    disk = {theme.load_theme(p)["name"] for p in list_theme_files()}
    members = {t.value for t in Theme}
    assert members == disk, (
        f"Theme enum out of sync with themes/. "
        f"Missing from enum: {disk - members}. Extra in enum: {members - disk}.")


def test_condition_enum_matches_yaml_files():
    disk = {name for name, _ in condition.list_conditions()}
    members = {c.value for c in Condition}
    assert members == disk, (
        f"Condition enum out of sync with conditions/. "
        f"Missing: {disk - members}. Extra: {members - disk}.")


def test_luts_enum_matches_cube_files():
    disk = {name for name, _ in list_luts()}
    members = {lut.value for lut in Luts}
    assert members == disk, (
        f"Luts enum out of sync with bundled .cube files. "
        f"Missing: {disk - members}. Extra: {members - disk}.")


def test_members_are_strings():
    """A StrEnum member IS its string value: usable anywhere a string is."""
    assert Theme.PORTRA_400 == "portra_400"
    assert isinstance(Condition.NEON_NIGHT, str)
    assert f"{Condition.NIGHT_FLASH}" == "night_flash"     # __str__ == value
    assert Theme("portra_400") is Theme.PORTRA_400          # raw string round-trips


def test_members_resolve_through_the_api():
    """An enum member works anywhere the raw string works."""
    cfg = theme.load_theme(Theme.EKTAR_100)
    assert cfg["name"] == "ektar_100"
    mult = condition.get_condition(Condition.NEUTRAL)
    assert mult == {"grain": 1.0, "chroma_noise": 1.0, "halation": 1.0}
