# Global Flood Database Feasibility

Status: **FINAL REAL-HISTORICAL ML FEASIBILITY: FAIL**.

This is the final real-historical-data fallback for the Jakarta MVP. It does not replace or weaken the earlier Sentinel-1 failure. Earth Engine was initialized with project `resilichain-aic-2026`, and the collection `GLOBAL_FLOOD_DB/MODIS_EVENTS/V1` was queried directly on 2026-08-12.

## Source semantics

The provider is the Global Flood Database, based on Dartmouth Flood Observatory events and the method published by Tellman et al. The official Earth Engine catalogue is <https://developers.google.com/earth-engine/datasets/catalog/GLOBAL_FLOOD_DB_MODIS_EVENTS_V1>. The collection contains 913 event products spanning 2000-02-17 through 2018-12-10.

The product represents maximum event flood extent and duration from MODIS at effective 250 m support. Direct Earth Engine projection inspection returned a nominal scale of 250 m and a geographic grid spacing of about 0.0022458 degrees. Any finer reduction grid is only an area-overlap approximation; it does not create 30 m observations.

Bands used:

- `flooded`: categorical maximum event flood extent;
- `clear_views`: number of clear-day observations;
- `clear_perc`: clear observations normalized by event duration, represented in the objects as a 0-1 fraction;
- `jrc_perm_water`: supplied permanent-water flag.

`duration`, event severity, casualties, displacement, and event ID are retained only for provenance or analysis. They are not predictive features.

The candidate target is `roadCorridorFloodExposure`: a road corridor intersects sufficient satellite-observed, non-permanent event flood extent. It is not a label for pavement inundation, road closure, water depth, passability, or vehicle failure.

## Jakarta discovery

The current OSM pilot remains fixed at `[106.755, -6.25, 106.94, -6.125]`. Nineteen Global Flood Database product geometries intersect it, but only two contain any non-permanent flood pixel inside it.

| DFO event | Date | Centroid/context | Raw flood in pilot | Non-permanent flood | Mean clear fraction | Decision |
|---|---|---|---:|---:|---:|---|
| 3251 | 2008-01-02 to 2008-01-06 | Centroid inside Jakarta pilot | 0.200454 km2 | 0.123465 km2 | 0.989121 | Candidate satellite event |
| 3280 | 2008-03-01 to 2008-04-03 | Centroid near 112.37 E, 7.13 S; one isolated pilot pixel | 0.061725 km2 | 0.061725 km2 | 0.990588 | Spatial/event-context uncertainty; all road labels excluded |

No independent BPBD/BNPB record for either exact event window was found in the existing project sources. They are therefore recorded as satellite-observed events, not independently officially confirmed events. The product also has no detected flood pixel in the pilot for DFO 4020, despite that product's Jakarta-area centroid and January 2013 window; footprint intersection alone is not treated as flood evidence.

## Road-corridor method

All 1,413 segment identities and geometries come from the existing real OSM runtime snapshot. No OSM download or rebuild occurred. Canonical processing uses:

- a 250 m buffer radius, equal to one effective source pixel;
- minimum clear fraction 0.75;
- minimum valid corridor observation fraction 0.80;
- permanent-water fraction below 0.20;
- positive exposure fraction at least 0.05;
- negative exposure fraction at most 0.001;
- `unknown` for intermediate exposure, inadequate coverage, permanent-water ambiguity, or uncertain event context.

A 30 m Earth Engine reduction scale approximates buffer-area overlap while retaining the explicit 250 m resolution class. `floodExposedLengthEquivalentM` is a corridor proxy computed as segment length times exposed fraction, not measured flooded road length.

## Canonical labels

| Event | Positive | Negative | Unknown/excluded |
|---|---:|---:|---:|
| DFO 3251 | 0 | 1,385 | 28 |
| DFO 3280 | 0 | 0 | 1,413 |
| Total | **0** | **1,385** | **1,441** |

The dataset contains 2,826 road-event observations. The canonical positive rate among usable labels is 0.0.

## Sensitivity

| Configuration | Positive | Negative | Unknown | Changed from canonical |
|---|---:|---:|---:|---:|
| Canonical: 250 m, quality 0.75, exposure 0.05 | 0 | 1,385 | 1,441 | 0 |
| 125 m radius | 0 | 1,389 | 1,437 | 4 |
| 375 m radius | 1 | 1,387 | 1,438 | 15 |
| Quality cutoff 0.50 | 0 | 1,385 | 1,441 | 0 |
| Quality cutoff 0.90 | 0 | 1,337 | 1,489 | 48 |
| Exposure threshold 0.02 | 1 | 1,385 | 1,440 | 1 |
| Exposure threshold 0.10 | 0 | 1,385 | 1,441 | 0 |

The single positive appears only after widening the corridor or lowering the exposure threshold. It is not stable under the canonical defensible definition and was not promoted to a positive label.

## Sanity check

`be/app/data/global-flood-db/label-samples.geojson` contains deterministic negative/unknown road examples together with all non-permanent source flood-pixel centres. The highest canonical road overlap is only 0.035234 and is correctly left unknown below the 0.05 threshold. No canonical positive exists to inspect.

## Final gate

| Criterion | Result | Reason |
|---|---|---|
| Multiple independent events | FAIL | Two raster intersections, only one with pilot-centred event context |
| Multiple positive event groups | FAIL | Zero canonical positive groups |
| Defensible negatives | PASS | 1,385 quality-controlled negatives |
| Usable class balance | FAIL | Zero positives |
| Event temporal split | FAIL | Train/validation/test generalization cannot be formed |
| Meaningful target semantics | PASS | Coarse corridor exposure is explicitly separated from road closure/pavement truth |
| Pre-event/static features available | PASS | OSM road class and length are available, but no feature matrix was built after failure |
| Leakage control | PASS | No same-event flood or post-event metadata was used as a feature |
| Between-event evaluation | FAIL | No positive event group exists |

Training Logistic Regression or Random Forest is prohibited. No ML metric may be reported. The active synthetic-label artifact remains unchanged.

March 2025 remains a separate offline demo/replay event. It is not a Global Flood Database training, validation, or test event, and its current flood geometry remains synthetic/approximate.

## Reproduction

```powershell
cd be
pip install -e ".[remote-sensing]"
python scripts/inspect_global_flood_database.py --project resilichain-aic-2026 --write
python scripts/build_global_flood_corridor_labels.py --project resilichain-aic-2026
python scripts/run_global_flood_feasibility_gate.py --write
```

The gate command intentionally exits with code 2 for `FAIL`. Runtime uses no Earth Engine, Overpass, or other external service.
