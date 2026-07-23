# LUT themes

Each `.cube` here is a 3D LUT; each `*.yaml` is a theme that applies one (a LUT
is a selectable look like any other theme, category `luts`). The `.cube` does
the color grade; the YAML adds a light, consistent finish (grain/sharpen).

## Add your own LUT

1. Drop a `.cube` (3D LUT) into this folder.
2. Add a `my_look.yaml` next to it:
   ```yaml
   # my_look
   # My custom LUT look.
   name: my_look
   lut: { file: MyLook.cube, intensity: 1.0 }
   grain: { luma: 0.01, size: 1.5 }
   ```
3. It shows up in `postfx list` and the contact sheet automatically, and is
   selectable with `--theme <name>` (or `load_theme("<name>")`).

External LUTs (outside the package) also work: point any theme's `lut.file` at
an absolute path to a user-supplied `.cube`.

## Bundled example LUT

`PunchOverlay.cube` is a free third-party LUT, bundled as a ready-to-run example
so the `luts` category works out of the box. It is not required for the pipeline —
point any theme's `lut.file` at your own `.cube`, or add a new LUT here (above).
If your LUT's source requests attribution, keep it when you redistribute.
