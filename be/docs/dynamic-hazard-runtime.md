# Dynamic Hazard Runtime

The backend supports two explicit analysis modes on `POST /api/simulations`:

- `historical-replay` preserves the Jakarta V1 historical pipeline. It is the default
  when `analysisMode` is omitted.
- `scenario-simulation` activates the frozen dynamic-hazard pipeline and requires
  `region: jakarta` plus a research scenario ID `Q1`, `Q2`, `Q3`, or `Q4`.

Operational vehicle and inventory overrides remain independent from hazard selection.

## Runtime pipeline

For scenario simulation, the backend loads an immutable 30Ã—4 representative sequence
from the promoted Phase 3A runtime artifact. The frozen Phase 2 Random Forest produces
`temporalHazardScore`. A frozen train-derived scenario anchor then supplies the
corresponding `relativeHazardIndex` validated in Phase 3B.

Existing road susceptibility remains the output of the unchanged historical road RF.
The runtime fusion is:

```text
dynamicRoadRiskScore = sigmoid(
    logit(staticRoadSusceptibility) + 1.5 * relativeHazardIndex
)
```

Beta `1.5` is a frozen policy/sensitivity parameter selected by Phase 3B invariants and
NetworkX propagationâ€”not fitted against road-level dynamic labels.

## Semantics and compatibility

`temporalHazardScore`, `relativeHazardIndex`, and `dynamicRoadRiskScore` are relative,
scenario-conditioned research scores. They are not calibrated flood probabilities,
weather forecasts, road-closure forecasts, BMKG categories, or physical rainfall
measurements. Runtime metadata therefore reports `probabilityCalibrated: false`.

NetworkX still requires Low/Medium/High/Critical bands. Scenario simulation derives
these routing compatibility bands from the unchanged static thresholds (`0.25`,
`0.50`, `0.75`). They are not validated dynamic flood-severity classifications.

Historical replay never loads or applies temporal hazard. Its road scores, route
selection, disruption structure, and historical model provenance remain byte-stable
against the V1 golden contract. Recovery/OR-Tools behavior is unchanged in Phase 4.

## Request example

```json
{
  "scenarioId": "scenario-jakarta-20250304",
  "analysisMode": "scenario-simulation",
  "region": "jakarta",
  "rainfallScenario": "Q3"
}
```

The simulation response contains one `hazard` metadata object. Dynamic disruption
roads expose `dynamicRoadRiskScore`; the legacy `riskProbability` road field continues
to expose static road susceptibility. This separation prevents accidental probability
semantics while preserving existing clients. The unchanged routing interface still names its
continuous compatibility field loodExposureProbability; in scenario simulation that
value carries the uncalibrated dynamic score and must not be interpreted as a probability.

Known limitations include undocumented source-target provenance, transformed temporal
features without rainfall units, absence of calibrated dynamic road labels, and
Jakarta-only runtime scope.
