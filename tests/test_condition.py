import pytest

from postfx import condition


def test_six_conditions_present():
    names = [n for n, _ in condition.list_conditions()]
    assert names == [
        "neutral", "day_outdoor", "overcast",
        "indoor_evening", "neon_night", "night_flash",
    ]


def test_all_conditions_load_and_merge():
    for path in condition.list_condition_files():
        cfg = condition.load_condition(path)
        for key in condition.CONDITION_DEFAULTS:
            assert key in cfg, f"{path}: {key} not merged"
        assert cfg["description"], f"{path}: missing description"


def test_conditions_have_descriptions():
    for name, desc in condition.list_conditions():
        assert desc, f"{name} should have a description"


def test_default_is_neutral_identity():
    assert condition.DEFAULT_CONDITION == "neutral"
    assert condition.get_condition("neutral") == {
        "grain": 1.0, "chroma_noise": 1.0, "halation": 1.0}


def test_none_resolves_to_default():
    assert condition.get_condition(None) == condition.get_condition("neutral")


def test_get_condition_returns_only_multipliers():
    cond = condition.get_condition("day_outdoor")
    assert set(cond) == set(condition.CONDITION_DEFAULTS)  # no name/description


def test_resolve_by_short_and_full_name():
    a = condition.load_condition("day_outdoor")
    b = condition.load_condition("02_day_outdoor")
    assert a["name"] == b["name"] == "day_outdoor"


def test_resolve_unknown_raises():
    with pytest.raises(FileNotFoundError):
        condition.get_condition("no_such_condition_xyz")


def test_unknown_key_rejected():
    with pytest.raises(ValueError):
        condition.validate({"grain": 1.0, "bogus_key": 1.0})


def test_non_numeric_multiplier_rejected():
    """A non-numeric multiplier fails fast at validation, not deep in the
    pipeline. YAML null (`grain:`) is the common author slip."""
    with pytest.raises(ValueError):
        condition.validate({"grain": None})
    with pytest.raises(ValueError):
        condition.validate({"halation": [1.0, 2.0]})
    with pytest.raises(ValueError):
        condition.validate({"chroma_noise": True})


def test_missing_key_fills_neutral():
    """A partial condition leaves the omitted multipliers at 1.0 (no scaling)."""
    cfg = dict(condition.CONDITION_DEFAULTS)
    cfg.update({"grain": 2.0})
    assert cfg == {"grain": 2.0, "chroma_noise": 1.0, "halation": 1.0}


def test_night_flash_grainier_than_day_outdoor():
    assert (condition.get_condition("night_flash")["grain"]
            > condition.get_condition("day_outdoor")["grain"])


def test_neon_night_blooms_more_than_flash_but_less_grain():
    """The decoupled case: neon has the strongest halation yet less grain than
    flash — the three multipliers do not move together in lockstep."""
    neon = condition.get_condition("neon_night")
    flash = condition.get_condition("night_flash")
    assert neon["halation"] > flash["halation"]
    assert neon["grain"] < flash["grain"]
