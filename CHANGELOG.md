# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-09-22

### Added

- `our_choices` theme category: `fine_grain_light`, `fine_grain_medium`,
  `fine_grain_heavy` — texture-only finishes measured from published social
  stills (fine per-pixel luma grain, flat across brightness, colour untouched).
  `Theme.OurChoices` enum group; the category lists first.

### Changed

- `grain.size` may go below 1.0: below the 1024 px reference grid the grain gets
  finer, and at `size <= 1024 / long edge` it is plain per-pixel noise (the
  previous floor of 1.0 always produced upscaled, blob-like grain on images
  larger than 1024 px, which read as coarse when viewed small).
- Every built-in theme's grain re-tuned onto that finer grid: `size` 1.4–1.9 →
  0.5–0.68, `luma` ×1.1, `chroma` ×0.5 (per-pixel colour speckle reads
  stronger); Tri-X 400 and analog_35mm additionally softened (0.055 → 0.045).
  Measured on a 1920 px still: the grain's contribution when the image is viewed
  at 800 px drops from up to +0.010 to ≤ +0.005 residual std, while at 100% it
  rises — grain now shows on zoom and vanishes at feed size, as a phone photo's
  does. Colour and tone of every theme are unchanged.

## [1.0.1] - 2026-09-22

### Changed

- `cv2`, `PIL` and `yaml` are now imported inside the functions that use them
  instead of at module level. `import postfx` no longer loads OpenCV (~70-170 ms
  cold); the cost is paid once, on the first call that needs it. No API change.

## [1.0.0] - 2026-07-24

### Added

- Initial public release.
- Theme-based post-processing pipeline: white balance (Bradford), exposure,
  highlight rolloff, lift/gamma/gain, split toning, tone curve, vibrance +
  saturation, halation, distortion, chromatic aberration, vignette, black-point
  lift, clarity, grain, sharpen, and optional JPEG re-encode.
- 30 built-in themes (15 `signature` film-stock/industry looks, 15
  `experimental`) plus `.cube` 3D LUT support (a LUT is a selectable theme).
- Six shooting-condition profiles (`neutral`, `day_outdoor`, `overcast`,
  `indoor_evening`, `neon_night`, `night_flash`) as an independent
  grain/noise/halation axis. YAML-defined (like themes); the default `neutral`
  applies no scaling, so a theme's texture is used exactly as authored.
- `postfx` CLI (`run`, `sheet`, `list`) and a small Python API
  (`process_file`, `process`, `load_theme`, `get_condition`, …).
- Typed `StrEnum` names for the public API — `Theme`, `Condition`, `Luts` —
  for autocomplete and typo-checking; plain strings still work everywhere.
- Deterministic, resolution-independent grain (seed from the filename hash).
- 108 tests.

[1.1.0]: https://github.com/0xBeycan/postfx/releases/tag/v1.1.0
[1.0.1]: https://github.com/0xBeycan/postfx/releases/tag/v1.0.1
[1.0.0]: https://github.com/0xBeycan/postfx/releases/tag/v1.0.0
