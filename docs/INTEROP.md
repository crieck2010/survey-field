# INTEROP — downstream handoffs from survey-field

survey-field is build #1 of the SurveySuite desktop product. It owns the
**field → job** step: Emlid CSV in, validated canonical job out. Everything
downstream reads the `.sfield.json` job file (`survey-field/job` schema v1)
or uses the adapters in `field/adapters.py`, which return **plain data**
(dicts/lists) so this package keeps zero dependencies.

## Job file contract

```jsonc
{
  "format": "survey-field/job",
  "schema_version": 1,
  "generator": "survey-field 0.2.0",
  "project": {
    "name": "...", "crs": "NAD83(2011) / UTM zone 18N",
    "source_files": ["day1.csv"],
    "base_stations": [
      {"id": "BASE-1", "easting": ..., "northing": ..., "elevation": ...,
       "longitude": ..., "latitude": ..., "ellipsoidal_height": ...,
       "antenna_height_m": ..., "source": "csv", "n_points": 42}
    ],
    "sessions": [
      {"id": "2026-09-25_BASE-1", "base_station_id": "BASE-1",
       "date": "2026-09-25",
       "points": [
         {"name": "101", "code": "EP", "description": "...",
          "easting": ..., "northing": ..., "elevation": ...,
          "longitude": ..., "latitude": ..., "ellipsoidal_height": ...,
          "origin": "Global", "tilt_angle_deg": 0.8,
          "rms_e": 0.011, "rms_n": 0.010, "rms_u": 0.018, "rms_lateral": 0.015,
          "antenna_height_m": 2.0, "solution": "FIX", "correction_type": "RTK",
          "averaging_start": "2026-09-25T14:02:11.200000+00:00",
          "averaging_end": "...", "samples": 25, "pdop": 1.8,
          "baseline_m": 17.832, "meta": {}}
       ]}
    ]
  }
}
```

Conventions the consumer can rely on:

- All linear values are **metres** (imperial antenna heights converted on import).
- Base-station easting/northing/elevation are the base **antenna phase centre**
  (receiver already applied pole height + ARP→APC offset).
- `solution` ∈ `FIX | FLOAT | SINGLE | UNKNOWN`.
- Points with no usable coordinates never occur without a `no-position`
  validation **error**; duplicates without a `duplicate-name` error.

## CRS reprojection provenance (`field import --target-crs`, v0.2.0)

A geographic-CS export can be reprojected into a projected CRS at import
time via the optional survey-crs engine (`field/reproject.py`, lazy import).
The job file keeps schema v1: the provenance block is an **additive optional**
`crs_provenance` object on the project dict, so v1 files (no such key) still
read everywhere.

```jsonc
"crs_provenance": {
  "source_crs": {"name": "WGS 84", "epsg": 4326, "datum": "WGS 84 (G2296)",
                 "unit": "deg", "as_recorded_in_csv": "WGS 84"},
  "target_crs": {"name": "NAD83(2011) / New York Long Island (ftUS)",
                 "epsg": 6539, "datum": "NAD83(2011)", "unit": "ftUS"},
  "transform": {
    "applied": true, "n_points": 3,
    "survey_crs_version": "0.1.0", "backend": "internal",
    "datum_path": {"from_datum": "WGS 84 (G2296)", "to_datum": "NAD83(2011)",
                   "method": "null-approximation", "accuracy_horizontal_m": 2.0,
                   "region": "CONUS", "source": "Penn State GEOG 862 ...",
                   "warning": "Approximate identity shift (<=~2 m ...) ..."},
    "warnings": ["datum: Approximate identity shift (<=~2 m horizontal ...)"],
    "timestamp": "2026-09-26T22:31:00+00:00"
  },
  "notes": ["reprojected 3 point(s) from WGS 84 (EPSG:4326) to ..."]
}
```

Behaviour matrix (conservative v1 rules):

| CSV | `--target-crs` | result |
|---|---|---|
| geographic | absent | unchanged (lat/lon only) |
| geographic | present | points transformed; easting/northing filled; project CRS = target |
| projected | absent | unchanged |
| projected | same EPSG | no-op, informational note, `transform.applied: false` |
| projected | different EPSG | **loud refusal** (exit 1, no job file written) |
| projected | unresolvable source CS name | **loud refusal** (target cannot be verified) |

Datum-shift warnings from `TransformResult.warnings` are printed as
`crs warning:` lines in the import report and stored in
`transform.warnings`. Inter-datum results are survey-crs null
approximations — never present them as survey control.

## Handoff A — survey-cogo (drafting / inverses / traverses)

```python
from field.adapters import project_cogo_points
from field.jobfile import read_job
from cogo import Point, inverse, polygon_area

project = read_job("job.sfield.json")
pts = [Point(**kw) for kw in project_cogo_points(project)]  # kwargs: northing, easting, name, elevation
```

`project_cogo_points` skips points that have only geographic coordinates
(a geographic-CS export); reproject those first with survey-geodesy
(`geodesy.latlon_to_utm` or the project's Transverse Mercator) and the
`crs` string on the project tells you which one.

## Handoff B — survey-adjust (build #2: the adjustment workflow)

Fixed datum for the level net comes from the base stations:

```python
from field.adapters import to_adjust_control, to_adjust_observations
from field.jobfile import read_job
from adjust import DiffObservation, adjust_level_net, global_test

project = read_job("job.sfield.json")
fixed = to_adjust_control(project)          # {"BASE-1": 172.5, ...}
obs = [DiffObservation(**o) for o in to_adjust_observations(project)]
result = adjust_level_net(obs, fixed=fixed)
```

`to_adjust_observations` emits one elevation-difference observation per **FIX**
rover point: `delta_h = rover_elev − base_elev`, `sigma` from the point's
elevation RMS (falling back to lateral RMS, then 0.05 m). FLOAT/SINGLE points
are **excluded** — build #2 decides whether to down-weight or reject them;
nothing is silently dropped because the exclusion rule is documented here
and the raw points remain in the job file.

Suggested build-#2 responsibilities (not this package's):

1. Let the user pick/rename the held control (base ids → control names).
2. Decide the FLOAT/SINGLE policy (exclude, de-weight, or re-observe list).
3. Run `adjust_level_net` + `global_test`, write the adjustment report.
4. Write adjusted coordinates back into a new job-file revision
   (schema bump if fields change — coordinate with this package).

## Versioning

- `schema_version` bumps on any breaking job-file change; readers reject
  newer versions loudly rather than misreading coordinates.
- Additive point fields (new Emlid columns) go in as-is or under `meta`
  and do **not** bump the schema version.
