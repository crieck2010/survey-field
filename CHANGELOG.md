# Changelog

All notable changes to survey-field. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-09-26

### Added
- `field import --target-crs <name|EPSG>`: reproject a geographic-CS Emlid
  export into a projected CRS on import, wired to the survey-crs v0.1.0
  engine (new `field/reproject.py`). Accepts `EPSG:6539`, `6539`, or
  registry names via `crs.search`. Fills easting/northing, sets the project
  CRS to the target, and records a `crs_provenance` block in the job file:
  source/target CRS, survey-crs version, backend name, datum-path method +
  accuracy + warnings, and timestamp. Schema stays v1 (additive optional
  field; v1 files still read).
- `field inspect` displays the CRS provenance block, including the datum
  path and its warnings.
- Conservative v1 rules: a projected CSV already in the target CRS is a
  no-op with an informational note; a projected CSV in a *different* CRS
  than an explicitly requested target is refused loudly (never silently
  mixed); an unresolvable source CS name is refused the same way.
- Datum-shift warnings from survey-crs (e.g. the NAD83(2011)↔WGS 84 ~2 m
  null approximation) surface as `crs warning:` lines in the import report.
- `--target-crs` without survey-crs installed fails with an actionable
  `pip install survey-crs` message, never an ImportError traceback.

### Notes / limitations
- Base-station coordinates are not reprojected in v0.2.0 (points only).
- The survey-crs registry has no legacy NAD83(1986) codes, so
  `--target-crs EPSG:2263` fails cleanly and points at EPSG:6539
  (NAD83(2011) / New York Long Island (ftUS)).
- `to_adjust_control` / `to_adjust_observations` adapter shapes are
  unchanged (build #2 contract intact); `to_cogo_kwargs` now returns
  coordinates for reprojected points since they carry projected positions.

## [0.1.0] - 2026-09-26

First release: the field-data import engine for the SurveySuite desktop product
(build #1 of 5: import → adjustment workflow → drafting/deliverables →
drone basemap → desktop app).

### Added
- Emlid Flow / ReachView 3 CSV import, header-driven so all known export
  variants parse: ReachView 3 classic (17 col), Emlid Flow (29 col),
  Emlid Flow 360 (31+ col, incl. Tilt angle and Correction type), and the
  minimal PENZD import template. Unknown columns are preserved on each
  point's `meta` dict instead of dropped.
- Canonical job model: `Project` → `BaseStation` records + `RoverSession`
  objects (split on base × day) → `SurveyPoint`s, with a versioned
  `survey-field/job` JSON interchange format (`.sfield.json`).
- Validation with clear errors (duplicate point names, points with no
  position, RTK points with no base record) and warnings (FLOAT/SINGLE
  solutions, RMS over threshold, missing rover antenna height, high PDOP,
  long baselines, few averaged samples). Thresholds are configurable.
- Adapters producing plain-data handoffs for the sibling engines:
  `to_cogo_kwargs` / `project_cogo_points` for `cogo.Point`,
  `to_adjust_control` / `to_adjust_observations` for
  `adjust.adjust_level_net` / `adjust.DiffObservation`.
- CLI: `field import` (CSV → job file + validation report),
  `field inspect` (job summary, optional issue list),
  `field export` (job → flattened CSV or canonical JSON).
- Imperial-unit handling: antenna heights in feet converted to metres.
- docs/INTEROP.md with the exact downstream call shapes for build #2.
