from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression

from dynamic_hazard.common import (
    DEFAULT_ARTIFACT_DIR,
    SEED,
    feature_names,
    fit_preprocessor,
    load_frozen_model,
    load_selection_splits,
    save_json,
)

MODEL_ORDER = ["majority_class", "train_prevalence", "logistic_regression", "random_forest", "mlp", "GRU", "LSTM"]


def _rank(row: dict[str, Any]) -> tuple[float, float, float]:
    metrics = row["validation"]
    return metrics["prAuc"], metrics["f1"], -metrics["brier"]


def _best_by_family(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [max((row for row in rows if row["model"] == name), key=_rank) for name in MODEL_ORDER]


def _logistic_coefficients(best: dict[str, Any]) -> dict[str, list[dict[str, float | str]]]:
    train, _ = load_selection_splits()
    representation = best["representation"]
    processor = fit_preprocessor(train, representation)
    values = processor.transform(train)
    estimator = LogisticRegression(
        C=best["hyperparameters"]["C"],
        class_weight="balanced",
        max_iter=2000,
        random_state=SEED,
    ).fit(values, train.y)
    names = feature_names(train, representation)
    coefficients = estimator.coef_[0]
    positive = np.argsort(coefficients)[-10:][::-1]
    negative = np.argsort(coefficients)[:10]

    def rows(indices: np.ndarray) -> list[dict[str, float | str]]:
        return [{"feature": names[index], "coefficient": float(coefficients[index])} for index in indices]

    return {"strongestPositive": rows(positive), "strongestNegative": rows(negative)}


def summarize(output_dir: Path = DEFAULT_ARTIFACT_DIR) -> dict[str, Any]:
    candidates = json.loads((output_dir / "candidate_results.json").read_text(encoding="utf-8"))
    selection = json.loads((output_dir / "model_selection.json").read_text(encoding="utf-8"))
    test = json.loads((output_dir / "test_evaluation.json").read_text(encoding="utf-8"))
    best_rows = _best_by_family(candidates)
    frozen = load_frozen_model(output_dir / selection["selectedArtifact"])
    importance_order = np.argsort(frozen.estimator.feature_importances_)[-15:][::-1]
    selected_importance = [
        {"feature": frozen.feature_names[index], "importance": float(frozen.estimator.feature_importances_[index])}
        for index in importance_order
    ]
    logistic = next(row for row in best_rows if row["model"] == "logistic_regression")
    summary = {
        "experimentVersion": selection["experimentVersion"],
        "selectionPolicy": selection["selectionPolicy"],
        "comparison": best_rows,
        "selectedModel": selection["selectedModel"],
        "frozenTestEvaluation": test,
        "interpretability": {
            "selectedRandomForestFeatureImportance": selected_importance,
            "bestLogisticRegressionCoefficients": _logistic_coefficients(logistic),
            "warning": (
                "Features are transformed source values indexed by relative sequence position. Importance and "
                "coefficients are associations, not physical rainfall effects or causal explanations."
            ),
        },
        "errorAnalysis": {
            "validationConfusionMatrix": selection["selectedModel"]["validation"]["confusionMatrix"],
            "testConfusionMatrix": test["metrics"]["confusionMatrix"],
            "interpretation": (
                "At the frozen threshold, the selected model misses many positive targets in both validation "
                "and test. Test also contains false positives. Per-timestep dates and physical rainfall units are "
                "unavailable, so errors are not attributed to weather mechanisms."
            ),
        },
    }
    save_json(output_dir / "experiment_summary.json", summary)
    with (output_dir / "validation_comparison.csv").open("w", encoding="utf-8", newline="") as target:
        fieldnames = [
            "model",
            "representation",
            "precision",
            "recall",
            "f1",
            "prAuc",
            "rocAuc",
            "brier",
            "threshold",
            "complexity",
        ]
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        for row in best_rows:
            metrics = row["validation"]
            writer.writerow(
                {
                    "model": row["model"],
                    "representation": row["representation"],
                    "precision": metrics["precision"],
                    "recall": metrics["recall"],
                    "f1": metrics["f1"],
                    "prAuc": metrics["prAuc"],
                    "rocAuc": metrics["rocAuc"],
                    "brier": metrics["brier"],
                    "threshold": row["selectedThreshold"]["threshold"],
                    "complexity": row["complexity"],
                }
            )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize the frozen Phase 2 temporal-hazard experiment.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    args = parser.parse_args()
    print(json.dumps(summarize(args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
