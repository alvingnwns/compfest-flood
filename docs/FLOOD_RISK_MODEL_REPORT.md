# Flood-Risk Model Report

Status: **historical model not trained**.

The active artifact remains `flood-risk-1.0.0-synthetic-labels`. It is a technically real Logistic Regression `predict_proba` pipeline trained on synthetic labels and must not be described as a historical satellite-trained flood model.

No Logistic Regression/Random Forest historical comparison, event-level split, confusion matrix, PR-AUC, Brier score, calibration analysis, classification-threshold selection, or holdout evaluation was performed in Phase C because the label feasibility gate could not be reached.

The exact scientific claim remains: the runtime returns a synthetic-placeholder estimate of road inundation exposure risk. It does not predict road closure, vehicle failure, exact water depth, or guaranteed flooding.
