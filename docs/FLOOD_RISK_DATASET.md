# Flood-Risk Dataset Status

Status: **two real-data label attempts constructed; neither is suitable for supervised training**.

## Attempt 1: Sentinel-1 road-inundation evidence

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

## Attempt 2: Global Flood Database road-corridor exposure

The fallback dataset contains 2,826 observations for two products with non-permanent flood pixels in the pilot:

| Event | Positive | Negative | Unknown/excluded |
|---|---:|---:|---:|
| DFO 3251, January 2008 | 0 | 1,385 | 28 |
| DFO 3280, March-April 2008 | 0 | 0 | 1,413 |

DFO 3280 has an event centroid outside Jakarta and only an isolated pilot pixel, so every observation is unknown rather than being forced into either class. The canonical definition uses a 250 m corridor radius, at least 75% clear observation, at least 80% valid coverage, less than 20% permanent-water overlap, and at least 5% exposure for a positive.

The canonical labels are in `be/app/data/datasets/global_flood_road_corridor_labels.csv`. The exact event audit, sensitivity configurations, sample evidence, and final gate are in `be/app/data/global-flood-db/`.

Scientific feasibility gate: **FAIL**. The canonical positive count is zero, only one event has pilot-centred context, and no temporal/event split can evaluate generalization. No predictive feature matrix was built.
