from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

BE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BE_DIR / "data" / "dynamic-hazard" / "processed"
MANIFEST_PATH = DATA_DIR / "manifest.json"
DEFAULT_ARTIFACT_DIR = BE_DIR / "artifacts" / "dynamic-hazard" / "experiments" / "phase2"
SEED = 42
SplitName = Literal["train", "validation", "test"]


@dataclass(frozen=True)
class TemporalSplit:
    name: SplitName
    X: np.ndarray
    y: np.ndarray
    dates: np.ndarray
    stations: np.ndarray
    summary_features: np.ndarray
    summary_names: np.ndarray


@dataclass
class FittedPreprocessor:
    representation: str
    scaler: StandardScaler
    sequence_shape: tuple[int, int]

    def transform(self, split: TemporalSplit) -> np.ndarray:
        if self.representation == "flattened_sequence":
            values = split.X.reshape(len(split.X), -1)
        elif self.representation == "flattened_plus_source_summary":
            values = np.concatenate([split.X.reshape(len(split.X), -1), split.summary_features], axis=1)
        elif self.representation == "ordered_sequence":
            flat = split.X.reshape(-1, split.X.shape[-1])
            scaled = self.scaler.transform(flat)
            return scaled.reshape(split.X.shape).astype(np.float64)
        else:
            raise ValueError(f"Unknown representation: {self.representation}")
        return self.scaler.transform(values).astype(np.float64)


@dataclass
class FrozenTemporalModel:
    model_name: str
    representation: str
    threshold: float
    preprocessor: FittedPreprocessor | None
    estimator: Any
    feature_names: list[str]
    training_manifest_sha256: str
    seed: int

    def predict_proba(self, split: TemporalSplit) -> np.ndarray:
        values = split.X if self.preprocessor is None else self.preprocessor.transform(split)
        probability = self.estimator.predict_proba(values)
        if probability.ndim == 2:
            probability = probability[:, 1]
        return np.asarray(probability, dtype=np.float64)


class SplitAccessError(RuntimeError):
    pass


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_split(name: SplitName, *, allow_test: bool = False) -> TemporalSplit:
    if name == "test" and not allow_test:
        raise SplitAccessError("The test split is inaccessible during candidate selection.")
    path = DATA_DIR / f"temporal_{name}.npz"
    with np.load(path, allow_pickle=False) as payload:
        return TemporalSplit(
            name=name,
            X=payload["X"].astype(np.float64),
            y=payload["y"].astype(np.int64),
            dates=payload["dates"],
            stations=payload["stations"],
            summary_features=payload["sum_feats"].astype(np.float64),
            summary_names=payload["sum_names"],
        )


def load_selection_splits() -> tuple[TemporalSplit, TemporalSplit]:
    return load_split("train"), load_split("validation")


def fit_preprocessor(train: TemporalSplit, representation: str) -> FittedPreprocessor:
    if train.name != "train":
        raise ValueError("Preprocessing may only be fitted on the train split.")
    if representation == "flattened_sequence":
        values = train.X.reshape(len(train.X), -1)
    elif representation == "flattened_plus_source_summary":
        values = np.concatenate([train.X.reshape(len(train.X), -1), train.summary_features], axis=1)
    elif representation == "ordered_sequence":
        values = train.X.reshape(-1, train.X.shape[-1])
    else:
        raise ValueError(f"Unknown representation: {representation}")
    return FittedPreprocessor(representation, StandardScaler().fit(values), train.X.shape[1:])


def feature_names(split: TemporalSplit, representation: str) -> list[str]:
    channels = [str(value) for value in split.stations]
    if representation == "ordered_sequence":
        return channels
    names = [f"t-{split.X.shape[1] - step:02d}:{channel}" for step in range(split.X.shape[1]) for channel in channels]
    if representation == "flattened_plus_source_summary":
        names.extend(str(value) for value in split.summary_names)
    return names


def select_threshold(y_true: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    candidates = np.unique(np.concatenate([np.linspace(0.01, 0.99, 99), probability]))
    rows = []
    for threshold in candidates:
        predicted = (probability >= threshold).astype(int)
        rows.append(
            {
                "threshold": float(threshold),
                "f1": float(f1_score(y_true, predicted, zero_division=0)),
                "precision": float(precision_score(y_true, predicted, zero_division=0)),
                "recall": float(recall_score(y_true, predicted, zero_division=0)),
            }
        )
    return max(rows, key=lambda row: (row["f1"], row["recall"], row["precision"], -row["threshold"]))


def evaluate_probabilities(y_true: np.ndarray, probability: np.ndarray, threshold: float) -> dict[str, Any]:
    probability = np.asarray(probability, dtype=np.float64)
    if not np.isfinite(probability).all() or np.any((probability < 0) | (probability > 1)):
        raise ValueError("Predicted probabilities must be finite and within [0, 1].")
    predicted = (probability >= threshold).astype(int)
    quantiles = np.quantile(probability, [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1])
    calibration = []
    edges = np.linspace(0, 1, 6)
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        mask = (probability >= lower) & (probability < upper if upper < 1 else probability <= upper)
        if mask.any():
            calibration.append(
                {
                    "lower": float(lower),
                    "upper": float(upper),
                    "count": int(mask.sum()),
                    "meanPredicted": float(probability[mask].mean()),
                    "observedRate": float(y_true[mask].mean()),
                }
            )
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, predicted)),
        "rocAuc": float(roc_auc_score(y_true, probability)),
        "prAuc": float(average_precision_score(y_true, probability)),
        "brier": float(brier_score_loss(y_true, probability)),
        "confusionMatrix": confusion_matrix(y_true, predicted, labels=[0, 1]).tolist(),
        "probabilityDistribution": {
            name: float(value)
            for name, value in zip(["minimum", "p10", "p25", "median", "p75", "p90", "maximum"], quantiles, strict=True)
        },
        "calibration": calibration,
    }


def class_weights(y: np.ndarray) -> np.ndarray:
    negative = len(y) / (2 * np.count_nonzero(y == 0))
    positive = len(y) / (2 * np.count_nonzero(y == 1))
    return np.where(y == 1, positive, negative).astype(np.float64)


def save_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def save_frozen_model(path: Path, model: FrozenTemporalModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path, compress=3)


def load_frozen_model(path: Path) -> FrozenTemporalModel:
    model = joblib.load(path)
    if not isinstance(model, FrozenTemporalModel):
        raise TypeError("Artifact is not a FrozenTemporalModel.")
    return model
