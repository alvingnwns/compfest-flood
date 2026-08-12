# Flood Remote-Sensing Pipeline

Status: **BOTH REAL-HISTORICAL LABEL ATTEMPTS FAILED THE SCIENTIFIC GATE**.

Attempt 1, documented below, used Sentinel-1 event change detection and failed with zero defensible positive road labels. Attempt 2 used the validated Global Flood Database event product with a coarse road-corridor target and also failed with zero canonical positives and no event-level split. See [`GLOBAL_FLOOD_DATABASE_FEASIBILITY.md`](GLOBAL_FLOOD_DATABASE_FEASIBILITY.md). Neither failure is hidden or weakened.

## Attempt 1: Sentinel-1

Earth Engine was initialized against Google Cloud project `resilichain-aic-2026`. Credentials remain outside the repository. The read-only acquisition audit queried `COPERNICUS/S1_GRD` over the Jakarta study bounds for four authoritative flood events.

## Event and acquisition audit

| Event | Role | Authoritative source | Sentinel-1 result |
|---|---|---|---|
| 2020-01-01 | Train | BNPB | Usable ascending IW VV+VH acquisition on 2020-01-02, plus same-group dry baseline |
| 2021-02-20 | Train | BNPB | Usable descending IW VV+VH acquisition on 2021-02-21 UTC / 2021-02-22 WIB, plus same-group dry baseline |
| 2022-01-18 | Validation | BPBD DKI Jakarta | No acquisition during the event or within 48 hours; all road observations are unknown |
| 2025-03-04 | Independent holdout | BPBD DKI Jakarta | Nearest acquisitions were 2025-02-28 and 2025-03-12; all road observations are unknown |

The catalogue and exact acquisition metadata are stored in `be/app/data/flood-events/jakarta-events.json` and `sentinel-1-availability.json`. March 2025 was assigned as holdout before mask inspection and was not used to tune thresholds.

## Mask construction

Each usable event is processed only within a homogeneous instrument group: IW mode, VV+VH polarization, matching relative orbit, matching pass direction, and 10 m native pixel spacing. Its dry reference is the median of June-October acquisitions from the preceding year in the same group: 12 images for January 2020 and 7 for February 2021.

The event and baseline images receive a 30 m focal median. Candidate inundation requires both a VV decrease of at least 2.0 dB and a VH decrease of at least 1.5 dB. JRC Global Surface Water occurrence of at least 90% is masked as permanent water; terrain above 5 degrees is masked using Copernicus DEM. These thresholds are an explicit conservative operational hypothesis, not a validated Jakarta accuracy claim.

The mask is reduced over 15 m buffers around all 1,413 real OSM road segments. A road-event observation is:

- positive when valid coverage is at least 80%, permanent-water overlap is below 20%, flood fraction is at least 20%, and estimated inundated length is at least 30 m;
- negative when valid coverage is at least 80%, permanent-water overlap is below 20%, and flood fraction is at most 2%;
- unknown otherwise, including missing timely imagery.

Sensitivity analysis also tested three less restrictive pixel thresholds and three less restrictive road thresholds. None produced a positive road label for either usable event. This result is not reinterpreted as proof that flooding did not occur: Sentinel-1 change detection over dense urban roads is limited by layover, shadow, double-bounce, acquisition timing, and the mismatch between a narrow road and SAR resolution.

## Reproduction

```powershell
cd be
pip install -e ".[remote-sensing]"
python scripts/inspect_sentinel_availability.py --project resilichain-aic-2026 --write
python scripts/build_road_flood_labels.py --project resilichain-aic-2026 --write
python scripts/analyze_label_sensitivity.py --project resilichain-aic-2026 --write
python scripts/run_scientific_feasibility_gate.py --write
```

The final command intentionally exits with code 2 while the gate status is `FAIL`. Training must not proceed.

## Attempt 2: Global Flood Database fallback

`GLOBAL_FLOOD_DB/MODIS_EVENTS/V1` was inspected across its full 2000-2018 coverage. Nineteen product geometries intersect the fixed Jakarta pilot, but only two contain non-permanent flood pixels in the pilot; only one has a pilot-centred event context. A 250 m road-corridor overlay created 2,826 observations: 0 positive, 1,385 negative, and 1,441 unknown/excluded.

Sensitivity over 125/250/375 m corridor radii, 0.50/0.75/0.90 clear-observation cutoffs, and 0.02/0.05/0.10 positive exposure thresholds produced at most one unstable positive. Thresholds were not selected to force class support.

The final fallback gate is `FAIL`. Feature engineering and model training stopped. The transparent synthetic runtime baseline remains active.
