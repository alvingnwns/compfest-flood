# Flood-risk model artifact

`flood_risk_model.joblib` contains the full preprocessing pipeline and selected Random Forest used through `predict_proba`. Its target is `roadCorridorFloodExposure`; labels are derived from real Global Flood Database observations over real OSM road corridors in multiple Indonesian regions.

The artifact is versioned as `indonesia-road-corridor-flood-exposure-v1` and records the feature schema/order, target semantics, validation-selected threshold, temporal/geographic split groups, metrics, training provenance, and scikit-learn version.

Regenerate it deterministically with:

```powershell
python scripts/train_indonesia_historical_flood_model.py
python scripts/evaluate_indonesia_historical_flood_model.py
```

Jakarta is deployment/demo inference only, not a labeled accuracy evaluation region. March 2025 flood geometry and business operations remain synthetic/simulated.
