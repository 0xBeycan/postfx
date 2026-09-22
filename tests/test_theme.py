import pytest

from postfx import theme


def test_categories_present():
    cats = theme.list_categories()
    assert "our_choices" in cats
    assert "signature" in cats
    assert "experimental" in cats
    assert "luts" in cats


def test_signature_and_experimental_counts():
    assert len(theme.list_theme_files(category="our_choices")) == 3
    assert len(theme.list_theme_files(category="signature")) == 15
    assert len(theme.list_theme_files(category="experimental")) == 15
    assert len(theme.list_theme_files(category="luts")) >= 1


def test_all_themes_load_and_merge():
    files = theme.list_theme_files()
    assert len(files) == (3 + 15 + 15
                          + len(theme.list_theme_files(category="luts")))
    for path in files:
        cfg = theme.load_theme(path)
        for key in theme.DEFAULTS:
            assert key in cfg, f"{path}: {key} not merged"


def test_themes_have_distinct_names_and_descriptions():
    themes = theme.list_themes()
    names = [n for n, _, _ in themes]
    assert len(set(names)) == len(names)
    for _, desc, _ in themes:
        assert desc, "every theme should have a description"


def test_list_themes_returns_category():
    for name, desc, category in theme.list_themes(category="signature"):
        assert category == "signature"


def test_unknown_key_rejected():
    with pytest.raises(ValueError):
        theme.validate({"white_balance": {"temp": 0}, "unknown_op": {}})


def test_non_mapping_op_rejected():
    with pytest.raises(ValueError):
        theme.validate({"exposure": 0.5})


def test_defaults_are_neutral():
    d = theme._deep_merge(theme.DEFAULTS, {})
    assert d["exposure"]["stops"] == 0.0
    assert d["vibrance"]["saturation"] == 1.0
    assert d["grain"]["luma"] == 0.0
    assert d["lut"]["file"] == ""


def test_resolve_by_short_and_full_name():
    a = theme.load_theme("portra_400")
    b = theme.load_theme("01_portra_400")
    assert a["name"] == b["name"] == "portra_400"


def test_resolve_unknown_raises():
    with pytest.raises(FileNotFoundError):
        theme.load_theme("no_such_theme_xyz")


def test_lut_theme_resolves_cube_path():
    cfg = theme.load_theme("punch_overlay")
    assert cfg["lut"]["file"].endswith(".cube")
    import os
    assert os.path.isfile(cfg["lut"]["file"])


def test_list_luts_finds_bundled_cube():
    luts = theme.list_luts()
    names = [n for n, _ in luts]
    assert "PunchOverlay" in names
