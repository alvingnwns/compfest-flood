# Flood-risk model artifact

`flood_risk_model.joblib` contains a real Logistic Regression estimator and scaler used through `predict_proba`. Its labels and input dataset are synthetic, so its metrics demonstrate only technical reproducibility—not real-world flood-prediction validity.

Regenerate it deterministically with `python scripts/train_flood_risk_model.py`. The JSON metadata records the model version, features, synthetic-data status, evaluation metrics, and scikit-learn version used to serialize the artifact.
