# Flood-Risk Dataset Status

Three historical-label attempts are preserved.

## Attempt 1: Sentinel-1 Jakarta — FAIL

5,652 road-event observations: 0 positive, 2,825 negative, and 2,827 unknown. Only two event groups had timely homogeneous Sentinel-1 acquisitions. March 2025 had no timely acquisition and remains unknown, not a negative. No model was trained from this attempt.

## Attempt 2: Global Flood Database Jakarta — FAIL

2,826 observations: 0 positive, 1,385 negative, and 1,441 unknown. Only two products contained non-permanent flood pixels in the pilot and only one had pilot-centred context. No event-level split was possible. No model was trained from this attempt.

## Attempt 3: Global Flood Database multi-region Indonesia — PASS

Objective discovery inspected 35 Indonesia-coded events and 3,981 event-region pairs before road labels. It selected 32 event-region groups across 13 regions and 8 provinces.

| Label | Count |
|---|---:|
| Positive | 2,219 |
| Negative | 26,911 |
| Unknown/excluded | 2,401 |
| Total | 31,531 |

The positive rate among usable rows is 7.6176%. Positives occur in 31 independent events and all 13 regions. Unknown rows are excluded from training and never recoded as negative.

Canonical labels use 250 m corridors, source/valid coverage >= 0.80, `clear_perc >= 0.75`, permanent water < 0.20, positive exposure >= 0.05, and negative exposure <= 0.001. The 100 m integration grid approximates corridor overlap only; the source support remains approximately 250 m.

The local feature table uses real OSM properties/geometry and causal prior-event history. Same-event flood evidence, event severity/duration/cause, post-event impacts, raw coordinates, and region identity are not predictive features.

See [`INDONESIA_HISTORICAL_FLOOD_DATASET.md`](INDONESIA_HISTORICAL_FLOOD_DATASET.md) and the artifacts under `be/app/data/indonesia-flood-ml/`.
