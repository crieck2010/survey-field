# survey-field

A pure-Python, dependency-free **field-data import engine** for the land-surveying suite: Emlid Flow / ReachView 3 CSV exports in, validated canonical survey jobs out.

This is build #1 of the SurveySuite desktop product (import → adjustment workflow → drafting/deliverables → drone basemap → desktop app). It is engine-only on purpose — no UI, no UI imports — so it can be imported by scripts, embedded in the desktop app, or installed as a library.

## Features

- **Emlid Flow / ReachView 3 CSV import** — header-driven parser that handles every known export variant (see *Format reference* below); unknown columns are preserved on each point's `meta` dict, never dropped
- **Canonical job model** — `Project` → base-station records + rover sessions (split on base × day) → points, serialised to a versioned `survey-field/job` JSON interchange file (`.sfield.json`)
- **Validation** — errors for duplicate point names, position-less points, and RTK points with no base record; warnings for FLOAT/SINGLE solutions, RMS over threshold, missing rover antenna height, high PDOP, long baselines, few averaged samples. All thresholds configurable
- **Downstream adapters** — plain-data handoffs shaped for `survey-cogo` (`cogo.Point` kwargs) and `survey-adjust` (`fixed={...}` datum + `DiffObservation` kwargs). Exact call shapes in `docs/INTEROP.md`
- **CLI** — `field import` a CSV to a job file, `field inspect` a job, `field export` a job back to CSV/JSON
- **Imperial handling** — antenna heights exported in feet are converted to metres on import

## Installation

Requires Python 3.9+. Zero runtime dependencies.

```bash
pip install .
# or, for development
pip install -e ".[dev]"  # dev extra not needed; pytest only for tests
pip install -e . && pip install pytest
```

## Quickstart

```bash
# Import an Emlid Flow export -> canonical job file (+ validation report)
field import examples/demo_emlid_flow.csv -o demo.sfield.json --name "Route 12 topo"

# Inspect the job
field inspect demo.sfield.json --issues

# Export the points back out as a flat CSV
field export demo.sfield.json -o points.csv --format csv
```

```python
from field.emlid import import_emlid_csv
from field.validate import validate_project
from field.adapters import project_cogo_points, to_adjust_control, to_adjust_observations
from field.jobfile import write_job

project = import_emlid_csv("day1.csv", project_name="Route 12 topo")
issues = validate_project(project)
for issue in issues:
    print(issue)

write_job(project, "day1.sfield.json")

# Hand the job to the sibling engines (see docs/INTEROP.md)
cogo_kwargs = project_cogo_points(project)   # -> cogo.Point(**kw)
fixed = to_adjust_control(project)           # -> adjust_level_net(fixed=fixed)
obs = to_adjust_observations(project)        # -> adjust.DiffObservation(**o)
```

## Format reference — Emlid CSV columns

Researched 2026-09-26 from Emlid docs, app changelogs, and real exports shared on the Emlid community forum. Column **order is irrelevant** to the parser; only header names matter.

| Variant | Columns |
|---|---|
| ReachView 3 classic (17) | Name, Easting, Northing, Elevation, Description, Easting RMS, Northing RMS, Elevation RMS, Lateral RMS, Antenna height, Solution status, Averaging start, Averaging end, Samples, Base easting, Base northing, Base elevation, Baseline |
| Emlid Flow (29) | + Code, Longitude, Latitude, Ellipsoidal height, Origin, Antenna height units, PDOP, Base longitude, Base latitude, Base ellipsoidal height, CS name |
| Emlid Flow 360 (31+) | + Tilt angle (after Origin), Correction type (after Solution status) |
| PENZD import template | Name, Easting, Northing, Elevation, Description, Code |

Notes:

- **Solution status**: `FIX`, `FLOAT`, `SINGLE`. FLOAT/SINGLE points import fine but raise validation warnings.
- **Base easting/northing/elevation** are the base's antenna *phase centre*: the receiver already applied the base pole height and the ARP→APC offset, so no height correction is applied on import.
- **Origin** is `Global` for GNSS-collected points.
- Timestamps look like `2026-09-25 14:02:11.2 UTC+00:00` and are normalised to ISO-8601.
- When the project uses a geographic (non-projected) coordinate system, the Easting/Northing/Elevation and Base easting/northing/elevation columns are blank and only Longitude/Latitude/Ellipsoidal height carry the position — the parser handles both.

## Validation rules

| Severity | Code | Meaning |
|---|---|---|
| error | `duplicate-name` | point name shot twice in one session |
| error | `no-position` | neither projected nor geographic coordinates |
| error | `base-missing` | FIX/FLOAT point with no base-station record |
| warning | `not-fixed` | FLOAT, SINGLE, or unrecorded solution |
| warning | `rms-lateral` / `rms-elev` | RMS above threshold (defaults 0.050 / 0.100 m) |
| warning | `no-antenna-height` | rover pole height missing (elevation is APC, not ground) |
| warning | `high-pdop` | PDOP above threshold (default 6.0) |
| warning | `long-baseline` | baseline above threshold (default 20 km) |
| warning | `low-samples` | FLOAT solution from few averaged epochs |

`field import` exits 1 when any error is present (the job file is still written); warnings alone exit 0.

## API reference

### `field.emlid`

| Function | Description |
|---|---|
| `import_emlid_csv(path, project_name=None)` | Parse a CSV file straight into a `Project` |
| `parse_emlid_csv(file)` | Parse an open file → `EmlidParseResult` (points + base info + dialect) |
| `detect_dialect(headers)` | `"emlid-flow-360"` / `"emlid-flow"` / `"reachview3"` / `"penzd-import"` / `"unknown"` |
| `build_project(points, base_info, name, source_file="")` | Assemble points into base stations + sessions |

### `field.models`

`Project` (`.iter_points()`, `.n_points()`, `.base_station(id)`, `.to_dict()`/`.from_dict()`), `BaseStation`, `RoverSession`, `SurveyPoint` (`.has_projected()`, `.has_geographic()`, `.has_any_position()`), `Solution` (`FIX`/`FLOAT`/`SINGLE`/`UNKNOWN`).

### `field.validate`

`validate_project(project, rms_lateral_warn=0.050, rms_elev_warn=0.100, pdop_warn=6.0, baseline_warn_m=20000.0, min_samples_float=10)` → `[ValidationIssue]` (errors first); `has_errors(issues)`.

### `field.jobfile`

`write_job(project, path)` / `read_job(path)` for `.sfield.json`; `dump_job` / `load_job` for dicts. Readers reject newer `schema_version`s loudly.

### `field.adapters`

`to_cogo_kwargs(point)` / `project_cogo_points(project)` → `cogo.Point` kwargs; `to_adjust_control(project)` → `fixed={base_id: elevation}`; `to_adjust_observations(project)` → `DiffObservation` kwargs (FIX points only); `job_summary(project)` → CLI/desktop stats.

## Testing

```bash
pip install pytest
python -m pytest
```

38 tests: all three Emlid CSV dialects plus the PENZD template, feet→metre conversion, base/session grouping, every validation rule, job-file round-trips and schema rejection, adapter shapes, and end-to-end CLI runs.

## Project structure

```
survey-field/
├── src/field/
│   ├── __init__.py      # version + model re-exports
│   ├── __main__.py      # python -m field
│   ├── models.py        # Project / BaseStation / RoverSession / SurveyPoint
│   ├── emlid.py         # header-driven Emlid Flow / ReachView 3 CSV parser
│   ├── validate.py      # errors + warnings with configurable thresholds
│   ├── jobfile.py       # versioned survey-field/job JSON interchange
│   ├── adapters.py      # plain-data handoffs for survey-cogo / survey-adjust
│   └── cli.py           # field import|inspect|export
├── tests/               # pytest suite (zero runtime deps; pytest is dev-only)
├── examples/demo_emlid_flow.csv
├── docs/INTEROP.md      # downstream contracts for build #2
├── CHANGELOG.md
└── pyproject.toml
```

## Conventions

- All linear values are **metres** after import.
- Parsing is header-driven, never positional: new Emlid columns degrade to `meta`, never to misread coordinates.
- The engine never touches the network or the disk except through `import_emlid_csv` / `jobfile` / the CLI; everything else is pure in-memory data.
- FLOAT/SINGLE points are imported and flagged, never silently dropped or silently "fixed".
