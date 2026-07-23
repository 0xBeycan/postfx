# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-24

### Added

- Initial public release.
- Theme-based post-processing pipeline: white balance (Bradford), exposure,
  highlight rolloff, lift/gamma/gain, split toning, tone curve, vibrance +
  saturation, halation, distortion, chromatic aberration, vignette, black-point
  lift, clarity, grain, sharpen, and optional JPEG re-encode.
- 30 built-in themes (15 `signature` film-stock/industry looks, 15
  `experimental`) plus `.cube` 3D LUT support (a LUT is a selectable theme).
- Three scene profiles (`day_outdoor`, `indoor_evening`, `night_flash`) as an
  independent grain/noise/halation axis.
- `postfx` CLI (`run`, `sheet`, `list`) and a small Python API
  (`process_file`, `process`, `load_theme`, `get_scene`, …).
- Deterministic, resolution-independent grain (seed from the filename hash).
- 90 tests.

[1.0.0]: https://github.com/0xBeycan/postfx/releases/tag/v1.0.0
