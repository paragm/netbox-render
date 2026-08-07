# Changelog

## v0.2.0 (2026-08-03)

Grid layout for dense shelf devices.

- Grid layout: auto-arrange bays in rows and columns when vertical stacking is too short
- Auto-calculation picks optimal column count by minimizing cell aspect ratio
- Per-device-type config overrides via `layouts` setting (key = device type slug)
- Config validation: invalid column values fall back to auto with a logged warning
- Empty padding cells rendered for partial last rows
- Updated docs and README with grid layout examples and configuration reference

## v0.1.5 (2026-08-01)

Packaging and metadata improvements. No code changes.

- Added classifiers, dev dependencies, ruff and pytest config to pyproject.toml
- Updated README compatibility table
- Fixed duplicate "Full Changelog" in release notes
- Auto-generate CHANGELOG from commits when no manual entry exists

## v0.1.4 (2026-07-31)

Cleaned up docs. No code changes.

## v0.1.3 (2026-07-31)

Docs and publishing prep. No code changes.

- Shelf device modeling guide
- CONTRIBUTING, SECURITY, issue/PR templates
- LICENSE (Apache-2.0)
- CI and publish workflows
- Before/after screenshots in README
- Verified compat with NetBox 4.6.5–4.6.7

## v0.1.0 (2025-12-01)

Initial release.

- Subdivide device bay rectangles in rack elevation SVGs
- Bay index numbering by name sort order
- Role-based colors on front face
- Clickable links to child devices
- Empty bay indicators
- Optional device type image rendering (`enable_images`)
- Startup signature check for `_draw_device`
- Compat: NetBox 4.6.x
