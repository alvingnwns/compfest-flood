# Indonesia Historical Flood Dataset

## Scope and decision

The product pilot remains DKI Jakarta. The supervised training population expands only to objectively selected Indonesian GAUL level-2 regions. Jakarta is deployment/demo inference, not a labeled validation region.

The primary source is `GLOBAL_FLOOD_DB/MODIS_EVENTS/V1` in Google Earth Engine. It is based on Dartmouth Flood Observatory events and has effective MODIS-scale support of approximately 250 m. The target is `roadCorridorFloodExposure`: a coarse road corridor intersects sufficient satellite-observed, non-permanent event flood. It is not road closure, pavement inundation, depth, passability, or vehicle failure.

## Deterministic discovery

The full discovery inspected 35 Indonesia-coded events and 443 GAUL level-2 regions, producing 3,981 event-region candidates. Inclusion required:

- at least 1 km² valid non-permanent flood;
- at least 0.1 km² flood over ESA WorldCover 2020 built-up class;
- source coverage at least 0.80;
- valid clear non-permanent coverage at least 0.80 using `clear_perc >= 0.75`;
- at most one region per event, ranked by built-up flood area, total flood area, valid observation, then stable region ID.

These rules were fixed before OSM extraction or road labels. WorldCover 2020 is only a deterministic logistics-relevance screen; it is not an event-time urban reconstruction or model feature. The full candidate list and exclusion reasons are in `be/app/data/indonesia-flood-ml/region-discovery.json`.

The result is 32 event-region groups, 13 regions, and 8 provinces spanning 2002-2016.

## Real OSM roads

OSMnx queried the full selected GAUL boundary using a `drive` network and retained motorway, trunk, primary, secondary, tertiary, and their link classes. Residential, service, path, track, and footway classes were excluded from training preparation. The 13 local snapshots contain 13,771 directed segments and 15,681,977 geometry bytes.

Each segment preserves a globally unique processed ID, region ID, OSM way IDs, `u`, `v`, `key`, highway, name, geometry, length, and directionality. Overpass and Earth Engine are preparation-only dependencies; training reruns and runtime use local artifacts.

## Corridor labels

The canonical corridor radius is 250 m. The Global Flood Database has effective approximately 250 m support; the 100 m reduction grid only integrates corridor area and does not create 100 m observational precision.

Quality rules are:

- source coverage >= 0.80;
- clear, non-permanent valid coverage >= 0.80;
- permanent-water fraction < 0.20;
- positive when valid flood exposure >= 0.05;
- negative when valid flood exposure <= 0.001;
- unknown otherwise.

Unknowns were never converted to negatives. The natural distribution, before weighting or resampling, is:

| Observation | Count |
|---|---:|
| Road-event rows | 31,531 |
| Positive | 2,219 |
| Negative | 26,911 |
| Unknown/excluded | 2,401 |
| Positive rate among usable | 7.6176% |

Canonical positives occur in 31 of 32 events and all 13 regions. The final 11-criterion scientific gate is `PASS`; its exact evidence is persisted in `scientific-feasibility-gate.json`.

## Sensitivity

At the canonical radius, lowering `clear_perc` from 0.75 to 0.50 changes only 6 of 31,531 labels. Raising it to 0.90 changes 1,278 rows, principally by moving marginal coverage to unknown, while retaining 2,110 positives. Positive threshold 0.02 produces 2,563 positives; threshold 0.10 produces 1,824. Positive support remains distributed across many events.

A limited 20-road comparison between 30 m and 100 m integration grids found identical canonical 250 m flood fractions and labels. Three differences occurred only for the 125 m radius sensitivity at the strict 0.80 coverage edge. The national canonical run therefore uses 250 m corridors and a documented 100 m integration grid.

## Non-leaky features

The model uses OSM road class, log length, directionality, geometry-derived sinuosity/orientation/vertex count, and causal prior-exposure history. For event T, prior counts/frequency/time-since-positive use only events before T. Tests confirm each segment's first event has zero prior observations.

Region/province identity, raw latitude/longitude, same-event flood exposure, quality masks, cause, duration, severity, and post-event impact are excluded.

## Split

- Train: 19,412 rows, 20 earlier events, 9 regions, 1,306 positives.
- Validation: 8,215 rows, 8 events from 2012 onward in non-test regions, 556 positives.
- Test: 1,503 rows, 4 events, 357 positives; all rows from wholly unseen Hulu Sungai Utara, Ogan Ilir, and Serdang Bedagai.

No event crosses split boundaries. Test regions are absent from both fitting and validation.

## Reproduction

```powershell
cd be
python scripts/discover_indonesia_flood_regions.py --project ARUNA-aic-2026 --write
python scripts/prepare_indonesia_region_roads.py --project ARUNA-aic-2026
python scripts/build_indonesia_flood_corridor_labels.py --project ARUNA-aic-2026
python scripts/run_indonesia_flood_feasibility_gate.py --write
python scripts/train_indonesia_historical_flood_model.py
python scripts/evaluate_indonesia_historical_flood_model.py
```

The first three commands require network access during preparation. Feature generation, training, evaluation, artifact loading, Jakarta inference, routing, recovery, and Historical Replay are offline.
