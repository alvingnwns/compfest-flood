# Temporal Hazard Phase 2 Artifacts

These files record an offline model benchmark for the probability of the source dataset's binary flood target
given a 30-step temporal feature sequence. They are experiment artifacts, not runtime application models.

Governance:

1. `candidate_results.json` was produced using train 2014-2018 and validation 2019 only.
2. `model_selection.json` froze the selected configuration, threshold, artifact SHA-256, and selection rationale.
3. `test_evaluation.json` was created once after selection. Its evaluator refuses to overwrite it.
4. No candidate was changed after the 2020 test result was observed.

Contents:

- `candidate_results.json`: all validation-only configurations.
- `model_selection.json`: immutable selection record.
- `selected_model.joblib`: selected experiment artifact; it is not loaded by `be/app`.
- `test_evaluation.json`: one-time 2020 evaluation.
- `experiment_summary.json`: final comparison, interpretability, and error summary.
- `validation_comparison.csv`: best validation configuration per model family.

Reproduction from `be/` requires the Phase 1 canonical processed files:

```powershell
$env:PYTHONPATH="scripts"
python -m dynamic_hazard.select_temporal_model
python -m dynamic_hazard.evaluate_selected_temporal_model
python -m dynamic_hazard.summarize_temporal_experiment
```

The second command intentionally fails if `test_evaluation.json` already exists. Reproduction must use a fresh
output directory to preserve the one-time test-access contract.
