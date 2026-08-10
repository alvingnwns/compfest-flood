import json
import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "app" / "data" / "datasets" / "synthetic_road_risk.csv"
MODELS_DIR = BASE_DIR / "app" / "models"
MODEL_PATH = MODELS_DIR / "flood_risk_model.joblib"
METRICS_PATH = MODELS_DIR / "flood_risk_metrics.json"

# Features we use for training
FEATURES = [
    "rainfall_mm",
    "hazard_score",
    "elevation_meters",
    "historical_flood_exposure",
    "drainage_pressure"
]
TARGET = "is_disrupted"

def train_model():
    if not DATASET_PATH.exists():
        print(f"Dataset not found at {DATASET_PATH}. Please run generate_synthetic_dataset.py first.")
        return

    # Load dataset
    df = pd.read_csv(DATASET_PATH)
    
    X = df[FEATURES]
    y = df[TARGET]

    # Split dataset
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train model
    print("Training Logistic Regression model...")
    model = LogisticRegression(random_state=42, class_weight="balanced")
    model.fit(X_train_scaled, y_train)

    # Predict and evaluate
    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]

    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_prob)

    print("Evaluation Results:")
    print(classification_report(y_test, y_pred))

    # Save metrics
    metrics = {
        "version": "flood-risk-1.0.0",
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "roc_auc": roc_auc,
        "features": FEATURES,
        "description": "Baseline Logistic Regression on synthetic road features."
    }
    
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to {METRICS_PATH}")

    # Save model and scaler as a single pipeline-like dictionary or tuple
    # We will save a dictionary containing both
    artifact = {
        "model": model,
        "scaler": scaler,
        "features": FEATURES,
        "version": "flood-risk-1.0.0"
    }
    
    joblib.dump(artifact, MODEL_PATH)
    print(f"Model artifact saved to {MODEL_PATH}")

if __name__ == "__main__":
    train_model()
