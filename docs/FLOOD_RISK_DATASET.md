# Flood-Risk Dataset Status

Status: **road-event labels constructed; not suitable for supervised training**.

The versioned dataset contains 5,652 observations from 1,413 real OSM road segments across four events. It contains 0 positive, 2,825 negative, and 2,827 unknown observations.

| Event | Role | Positive | Negative | Unknown |
|---|---:|---:|---:|---:|
| 2020-01-01 | Train | 0 | 1,413 | 0 |
| 2021-02-20 | Train | 0 | 1,412 | 1 |
| 2022-01-18 | Validation | 0 | 0 | 1,413 |
| 2025-03-04 | Holdout | 0 | 0 | 1,413 |

Unknown observations are excluded rather than forced negative. In particular, the validation and holdout events have no timely Sentinel-1 acquisition. March 2025 road reports are preserved as authoritative event evidence, but cannot become satellite-observed road labels without suitable imagery.

The canonical labels are in `be/app/data/datasets/historical_road_flood_labels.csv`; provenance, mask summaries, and sensitivity results are in `be/app/data/flood-events/`. No pre-event/context feature matrix was built because the label feasibility gate failed first. This ordering prevents post-event leakage and avoids spending downstream analysis on an invalid target.

Scientific feasibility gate: **FAIL**. There is no positive class, only two usable event groups, no usable validation event, and no usable independent holdout.
