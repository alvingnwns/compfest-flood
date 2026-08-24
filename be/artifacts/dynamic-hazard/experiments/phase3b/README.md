# Dynamic Hazard Phase 3B: Road-Risk Fusion Research

This directory evaluates transparent, deterministic fusion of the frozen Phase 2
temporal model with the existing Jakarta road-susceptibility model. It is offline
research only: no runtime service, API, frontend, routing implementation, threshold,
or simulation state is changed.

## Scientific semantics

`dynamicRoadRiskScore` is a scenario-conditioned relative road-risk score derived
from two different frozen signals:

- `relativeHazardIndex`: a train-only empirical percentile transform of the
  uncalibrated temporal hazard score; and
- existing road susceptibility: historical road-corridor flood-exposure
  susceptibility derived from OSM and historical exposure features.

The fused score is not a calibrated road flood probability, road flood forecast,
road-closure forecast, or real-time forecast.

## Candidate governance

The analysis evaluates multiplicative modulation, logit shift, and bounded
complement uplift at policy/sensitivity parameters 0.25, 0.5, 0.75, 1.0, and 1.5.
No parameter is fitted against fabricated road-level dynamic labels. Candidate
selection requires monotonic scenario effects, strict spatial ordering, meaningful
Q1-to-Q4 score and category movement, no saturation, and changes in at least 25% of
the 12 existing NetworkX OD paths.

Current static-model category thresholds are applied unchanged for sensitivity
analysis only. Their use here does not make the fused score calibrated.

## Artifacts

- `fusion_analysis.json`: input provenance, normalization, all candidate results,
  invariants, category sensitivity, selection rule, and limitations.
- `fusion_comparison.csv`: compact method × parameter × scenario distributions.
- `routing_sensitivity.json`: isolated calls through the existing NetworkX service
  for all candidate/scenario combinations.
- `selected_fusion.json`: frozen research selection record; not runtime config.
- `selected_road_scores.csv`: all 1,413 real computational segment IDs, OSM and
  geometry references, static scores, and selected Q1-Q4 dynamic scores.

## Reproduce

From `be`, with the backend environment installed:

```powershell
$env:PYTHONPATH = 'scripts'
python -m dynamic_hazard.analyze_road_risk_fusion
python -m dynamic_hazard.summarize_road_risk_fusion
```

The analysis verifies both frozen model hashes and confirms that model, road-feature,
and routing-graph hashes remain unchanged after offline routing evaluation.
