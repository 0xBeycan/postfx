import pytest

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
    assert Theme.Signature.PORTRA_400 == "portra_400"
    assert isinstance(Condition.NEON_NIGHT, str)
    assert f"{Condition.NIGHT_FLASH}" == "night_flash"     # __str__ == value


def test_theme_namespace_behaves_like_a_flat_enum():
    """The `Theme` namespace keeps flat-enum ergonomics over grouped members."""
    # round-trip: a raw value resolves back to the exact member object
    assert Theme("portra_400") is Theme.Signature.PORTRA_400
    assert Theme("clean_editorial") is Theme.Experimental.CLEAN_EDITORIAL
    # membership
    assert "portra_400" in Theme
    assert "not_a_theme" not in Theme
    # an invalid value raises, like StrEnum(...)
    with pytest.raises(ValueError):
        Theme("not_a_theme")
    # iteration spans every group and is duplicate-free
    members = list(Theme)
    assert len(members) == len({m.value for m in members})
    assert Theme.Signature.PORTRA_400 in members
    assert Theme.Experimental.SUNBLEACHED in members


def test_theme_groups_match_disk_categories():
    """Each nested group holds exactly its category's theme names."""
    for group_name, category in [("Signature", "signature"),
                                 ("Luts", "luts"),
                                 ("Experimental", "experimental")]:
        group = getattr(Theme, group_name)
        members = {m.value for m in group}
        disk = {theme.load_theme(p)["name"]
                for p in list_theme_files(category)}
        assert members == disk, (
            f"Theme.{group_name} out of sync with themes/{category}/. "
            f"Missing: {disk - members}. Extra: {members - disk}.")


def test_members_resolve_through_the_api():
    """An enum member works anywhere the raw string works."""
    cfg = theme.load_theme(Theme.Signature.EKTAR_100)
    assert cfg["name"] == "ektar_100"
    mult = condition.get_condition(Condition.NEUTRAL)
    assert mult == {"grain": 1.0, "chroma_noise": 1.0, "halation": 1.0}
