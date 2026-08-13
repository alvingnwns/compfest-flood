# Dynamic Hazard Phase 3A: Rainfall Scenario Feasibility

This directory contains offline, research-only analysis of temporal rainfall-pattern
scenarios. It does not define runtime presets, API behavior, frontend behavior, or
road-risk fusion logic.

## Scope and data governance

- Scenario definitions are derived from the 2014-2018 training split only.
- The month channel is excluded from rainfall-pattern features.
- Validation is used only after derivation to assess stability.
- The held-out test split is not accessed.
- All reported rainfall descriptors use transformed source-feature values. Physical
  rainfall units and the original transformations are unavailable, so these values
  must not be interpreted as millimetres or operational thresholds.
- `temporalHazardScore` is the frozen Phase 2 random-forest output. It is an
  uncalibrated relative score, not a literal flood probability.

## Artifacts

- `scenario_analysis.json`: methods, governance metadata, score separation,
  validation stability, month-versus-station evidence, limitations, and decision gate.
- `scenario_comparison.csv`: compact train/validation comparison for quantile and
  clustering groups.
- `representative_sequences.npz`: deterministic representatives selected from real
  training samples; no synthetic station values are generated.

## Reproduce

From the `be` directory, with the backend environment installed:

```powershell
$env:PYTHONPATH = 'scripts'
python -m dynamic_hazard.analyze_rainfall_scenarios
```

The script verifies the frozen Phase 2 model SHA-256 before scoring and never
retrains it. Re-running with the same inputs and dependencies produces the same
artifact contents.

## Interpretation boundary

The `GO` decision means the discovered scenario groups are sufficiently distinct,
stable, and not purely month-driven to justify a later research phase. It is not
approval to expose these scenarios as production rainfall controls. Runtime use
requires separate semantic validation, calibration, provenance, and integration
work.
