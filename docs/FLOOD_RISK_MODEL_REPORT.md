# Flood-Risk Model Report

Status: **Indonesia multi-region scientific gate PASS; historical model active with limited geographic generalization**.

The two Jakarta-only attempts remain valid failures:

1. Sentinel-1: 5,652 observations, zero positive, only two usable event groups, no usable March 2025 holdout.
2. Global Flood Database Jakarta: 2,826 observations, zero canonical positive, no event split.

Phase D objectively selected 32 event-region groups across 13 Indonesian regions before inspecting road labels. The canonical dataset has 2,219 positive, 26,911 negative, and 2,401 unknown observations. Positive support exists in 31 events and all 13 regions, so the final scientific gate passed before feature engineering.

## Models and split

Logistic Regression and Random Forest use a sklearn preprocessing pipeline. Algorithm and threshold were selected from validation only. The final test contains three entire regions absent from fitting and validation.

| Model | Precision | Recall | F1 | ROC-AUC | PR-AUC | Brier |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.436 | 0.210 | 0.284 | 0.659 | 0.444 | 0.207 |
| Random Forest | 0.577 | 0.168 | 0.260 | 0.636 | 0.429 | 0.175 |
| Majority-negative baseline | 0.000 | 0.000 | 0.000 | 0.500 | 0.238 | 0.238 |
| Causal history baseline | 0.857 | 0.101 | 0.180 | 0.548 | 0.300 | 0.218 |

Random Forest was selected from validation because it had higher PR-AUC, F1, ROC-AUC, and better Brier score there. Its validation-selected threshold is 0.55. The final unseen-region test was not used for tuning.

The selected model beats both trivial baselines overall on unseen regions, including PR-AUC, F1, recall, and Brier, but its positive recall is only 0.168. Region results vary materially: Hulu Sungai Utara F1 is 0.489, Ogan Ilir F1 is 0.163, and Serdang Bedagai F1 is 0.000. Cross-region generalization is measurable but limited.

## Calibration and ablation

Final-test Brier score is 0.175. Calibration bins show underprediction below 0.2 and some overprediction from approximately 0.3-0.9; probabilities are evaluated but not perfectly calibrated. No calibration model was fitted to final-test groups.

The largest impurity importances are log segment length and causal exposure-history features; these are associations, not causes. Removing historical exposure reduces test PR-AUC from 0.429 to 0.358 but increases thresholded recall, demonstrating instability rather than a single-feature causal claim. Geometry and road-class ablations are recorded in `model-audit.json`.

## Jakarta inference and runtime

The artifact is `be/app/models/flood_risk_model.joblib`, version `indonesia-road-corridor-flood-exposure-v1`. It contains the full preprocessing pipeline, Random Forest, feature schema/order, threshold, split groups, metrics, target semantics, training provenance, and sklearn version.

All 1,413 Jakarta OSM roads infer successfully offline. Numeric feature ranges fall inside training ranges, but Jakarta includes `residential` and `service` road categories absent from the logistics-filtered training data. The encoder handles them without failure, but Jakarta is **PARTIALLY OUT-OF-DISTRIBUTION**. Jakarta probabilities are deployment/demo inference, not Jakarta accuracy evidence.

FastAPI rejects missing/invalid historical artifacts rather than silently falling back to the synthetic model. Batched `predict_proba` takes approximately 1.44 seconds for all Jakarta roads, and cached per-road lookup takes approximately 0.08 seconds total. A deterministic test shows real model probabilities change the OSM NetworkX route from 33 to 31 segments for `wh-west -> store-a`; the resulting routes propagate through CP-SAT and Manufacturing, Logistics, Commerce, and KPI computations.

March 2025 remains a demo-only Historical Replay scenario with approximate/synthetic flood geometry and simulated business data. It is not a labeled model test event.
