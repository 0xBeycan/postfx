# CLAUDE.md — postfx

Pure-Python, **CPU** image post-processing pipeline that gives images a
theme-based "look". No GPU, no ML. All code and docs are in English.

## Layout

| Path | Contents |
|------|----------|
| `postfx/color.py` | sRGB↔linear, Bradford white-balance matrices |
| `postfx/ops.py` | Atomic ops (pure functions) + `.cube` 3D LUT parse/apply |
| `postfx/pipeline.py` | Fixed processing order / orchestration |
| `postfx/theme.py` | YAML load, validation, DEFAULTS merge, categories |
| `postfx/scenes.py` | 3 scene profiles (grain/noise/halation multipliers) |
| `postfx/imgio.py` | Load/save (resolution preserved), deterministic seed |
| `postfx/sheet.py` | Contact-sheet (theme grid) generation |
| `postfx/cli.py` | `run` / `sheet` / `list` |
| `postfx/themes/{signature,experimental,luts}/` | Theme YAMLs + bundled `.cube` |
| `tests/` | pytest suite |

## Commands

```bash
uv sync --extra dev            # or: pip install -e ".[dev]"
uv run pytest -q               # tests
python -m postfx list          # themes (by category) + scenes
python -m postfx run --input <file|folder> --theme <name> --scene <name> --out <dir>
python -m postfx sheet --input <image> --out sheet.jpg
uv build                       # build wheel + sdist into dist/
```

## Invariants (do not break)

- **Processing order is fixed** (`pipeline.py`). Halation is in linear space, the
  LUT right after linear→sRGB, grain in sRGB. Don't reorder.
- **Every op is a pure function**: `(array, params) -> new array`, no side effects.
- **All intermediate work is float32 `[0,1]` RGB.** Convert to 8-bit only on save.
- **Resolution & aspect preserved** — no crop/resize (except the sheet preview).
- **Determinism**: grain seed from the filename hash (`imgio.seed_from_path`).
  Same image + theme = byte-identical output. Keep it.
- **Theme validation**: an unknown key raises; a missing key fills from `theme.DEFAULTS`.
- Keep the runtime deps minimal: `numpy, opencv-python-headless, Pillow, PyYAML`.

## Adding a theme / LUT

- Theme: add `postfx/themes/<category>/<name>.yaml` — the first comment lines are
  name / character / suited content; parameters follow (see `README.md`). No
  placeholder values — actually tune it. Verify with `sheet` + `pytest`.
- LUT: drop a `.cube` (3D) into `postfx/themes/luts/` + a YAML with
  `lut: { file: X.cube }`. See `postfx/themes/luts/README.md`.

## Release

Version is single-sourced from `postfx/__init__.py` (`__version__`). To publish:
bump it, update `CHANGELOG.md`, tag `vX.Y.Z`, and let the GitHub `publish`
workflow build + upload to PyPI (trusted publishing).
