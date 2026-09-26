# Changelog

All notable changes to survey-field. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

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
