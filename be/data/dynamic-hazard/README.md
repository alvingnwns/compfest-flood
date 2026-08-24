# Jakarta Dynamic-Hazard Research Dataset

This directory isolates the research/training data for ARUNA V2 from `be/app/data`, which remains the
runtime data package for the Jakarta historical replay.

## Intended use

The released dataset can support experiments of the form:

```text
source-provided 30-step temporal rainfall features
  -> temporal flood/hazard model
  -> Jakarta-level dynamic hazard probability
```

It does **not** directly support `rainfall -> exact flooded road`. The released target is one binary target per
temporal sample, not a road-level or graph-node-level label. It must not be mapped to the existing 1,413 OSM
road segments without separate, defensible alignment and labels.

The source archive describes three station-related channels (`tj_priok`, `banten`, and `kemayoran`) plus a
`month` channel. Values are already transformed/scaled and include negative values. The released material does
not document physical rainfall units or transformation parameters, so these values must not be described as raw
millimetres.

## Source and immutable raw data

`raw/Dataset_FloodRisk_Jakarta.zip` is immutable source material. Scripts read it in place and never modify or
silently overwrite it. The archive contains derived features only; its README says raw rainfall, DEM, OSM, and
drainage files are excluded because of licensing restrictions.

The source documents the target only as a binary flood-prediction target. Therefore the canonical manifest uses:

- `targetSemantics`: `binary flood target as provided by source dataset`
- `groundTruthSource`: `not documented in released dataset`

No BPBD, satellite, sensor, or other ground-truth provenance is inferred.

## Temporal split

The source-provided split is chronological by reference date:

| Split | Samples | Reference-date range | Positive targets |
|---|---:|---|---:|
| Train | 335 | 2014-02-05 to 2018-12-26 | 50 |
| Validation | 67 | 2019-01-31 to 2019-12-27 | 10 |
| Test | 67 | 2020-01-31 to 2020-12-26 | 11 |

Each temporal tensor has shape `(samples, 30, 4)`. No date or exact 30-step sequence is shared across splits.
Neighboring samples commonly share historical timesteps because the source uses sliding windows; this is not by
itself target leakage. However, the archive does not release a date for every timestep or document precise
reference-date/window alignment. Consequently, independent proof that every window excludes future observations
is not possible from the released derivative artifacts alone.

## Spatial and graph findings

- Spatial embeddings: 314 IDs x 64 dimensions.
- Graph-node positions: 384 IDs with `x` and `y` coordinates.
- All 314 spatial IDs occur in the node-position table; 70 graph IDs have no spatial embedding.
- Graph metadata reports 384 nodes and 297 directed edges.
- No raw edge list, `edge_index`, adjacency matrix, source/target edge table, or serialized graph object is present.
- The three released graph-embedding arrays contain 469 rows x 48 dimensions, but all 469 rows are exactly the
  same vector.

The released graph representation is static across temporal samples and therefore does not provide
sample-specific dynamic spatial flood state. This is a limitation of the released artifacts, not evidence of a
source bug. Spatial/GNN features are excluded from the initial temporal baseline until raw graph structure,
alignment, and defensible node-level targets are available.

## Canonical processed contract

`prepare_dynamic_hazard_dataset.py` converts only the unsafe object-typed date arrays to fixed-width ISO strings.
All numeric arrays and source feature names are preserved. Conceptually, each record exposes:

```json
{
  "referenceDate": "YYYY-MM-DD",
  "rainfallSequence": "30 x 4 source-preserved numeric tensor",
  "target": "0 or 1",
  "split": "train | validation | test"
}
```

Generated files are:

- `processed/temporal_train.npz`
- `processed/temporal_validation.npz`
- `processed/temporal_test.npz`
- `processed/manifest.json`

NPZ members are written in a stable order with fixed ZIP metadata. Use `--processing-timestamp` or
`SOURCE_DATE_EPOCH` when byte-for-byte deterministic manifest reproduction is required.

## Reproduction

From `be/`:

```powershell
python scripts/inspect_dynamic_hazard_dataset.py
python scripts/prepare_dynamic_hazard_dataset.py
python -m pytest tests/test_dynamic_hazard_dataset.py -p no:cacheprovider
```

## Architecture boundaries

- **Temporal hazard:** dynamic environmental probability derived from temporal rainfall features.
- **Road susceptibility:** existing RF estimate based on OSM/static historical road exposure features.
- **Operational state:** inventory, vehicles, orders, production, and capacity used by the supply-chain optimizer.

These are separate concepts. This Phase 1 dataset is not runtime application data and changes none of the Jakarta
historical replay, NetworkX routing, or OR-Tools behavior.
