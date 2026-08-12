# Flood-Risk Model Report

Status: **historical model training prohibited by the scientific feasibility gate**.

The gate was run after authoritative event cataloguing, Sentinel-1 availability inspection, homogeneous grouping, dry-baseline construction, flood masking, quality masking, and OSM road overlay. It failed because the resulting dataset has zero defensible positive labels, only two usable event groups, no usable validation event, and no usable March 2025 holdout.

Consequently, Logistic Regression and Random Forest were not trained or compared. No historical Precision, Recall, F1, ROC-AUC, PR-AUC, calibration, or holdout metric exists, and none is inferred or fabricated.

The active artifact remains `flood-risk-1.0.0-synthetic-labels`. It is a technically real Logistic Regression `predict_proba` pipeline trained on synthetic labels. Those probabilities continue to affect the real OSM NetworkX route costs and propagate into the existing OR-Tools recovery and KPI calculations, but they must not be described as satellite-trained historical road risk.

Historical Replay remains fully offline. The exact scientific claim remains: runtime returns a synthetic-placeholder estimate of road inundation exposure risk; it does not predict road closure, vehicle failure, exact water depth, or guaranteed flooding.
