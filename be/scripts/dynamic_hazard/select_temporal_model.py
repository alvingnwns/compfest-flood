from __future__ import annotations

import argparse
import copy
import json
import warnings
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier

from dynamic_hazard.common import (
    DEFAULT_ARTIFACT_DIR,
    MANIFEST_PATH,
    SEED,
    FrozenTemporalModel,
    class_weights,
    evaluate_probabilities,
    feature_names,
    file_sha256,
    fit_preprocessor,
    load_manifest,
    load_selection_splits,
    save_frozen_model,
    save_json,
    select_threshold,
)
from dynamic_hazard.recurrent import NumpyRecurrentClassifier


def _evaluate_candidate(
    name: str,
    representation: str,
    estimator: Any,
    validation_values: np.ndarray,
    validation_y: np.ndarray,
    hyperparameters: dict[str, Any],
    complexity: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    probability = estimator.predict_proba(validation_values)
    if probability.ndim == 2:
        probability = probability[:, 1]
    threshold = select_threshold(validation_y, probability)
    return {
        "model": name,
        "representation": representation,
        "hyperparameters": hyperparameters,
        "complexity": complexity,
        "selectedThreshold": threshold,
        "validation": evaluate_probabilities(validation_y, probability, threshold["threshold"]),
        **(extra or {}),
    }


def _fit_mlp(train_values, train_y, validation_values, validation_y, architecture, alpha):
    estimator = MLPClassifier(
        hidden_layer_sizes=architecture,
        alpha=alpha,
        batch_size=32,
        learning_rate_init=0.001,
        max_iter=1,
        warm_start=True,
        shuffle=True,
        random_state=SEED,
    )
    weights = class_weights(train_y)
    best_estimator = None
    best_loss = float("inf")
    best_epoch = 0
    stale = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        for epoch in range(1, 251):
            estimator.fit(train_values, train_y, sample_weight=weights)
            probability = np.clip(estimator.predict_proba(validation_values)[:, 1], 1e-8, 1 - 1e-8)
            validation_loss = -float(
                np.mean(validation_y * np.log(probability) + (1 - validation_y) * np.log(1 - probability))
            )
            if validation_loss < best_loss - 1e-6:
                best_loss = validation_loss
                best_epoch = epoch
                best_estimator = copy.deepcopy(estimator)
                stale = 0
            else:
                stale += 1
            if stale >= 30:
                break
    return best_estimator, {"bestEpoch": best_epoch, "epochsRun": epoch, "bestValidationLogLoss": best_loss}


def run_selection(output_dir: Path = DEFAULT_ARTIFACT_DIR) -> dict[str, Any]:
    if (output_dir / "test_evaluation.json").exists():
        raise RuntimeError("Model selection is frozen because a test evaluation already exists.")
    train, validation = load_selection_splits()
    manifest = load_manifest()
    candidates: list[tuple[dict[str, Any], FrozenTemporalModel]] = []

    majority_probability = np.zeros(len(validation.y))
    majority_metrics = evaluate_probabilities(validation.y, majority_probability, 0.5)
    candidates.append(
        (
            {
                "model": "majority_class",
                "representation": "constant",
                "hyperparameters": {},
                "complexity": "trivial",
                "selectedThreshold": {"threshold": 0.5, "f1": 0.0, "precision": 0.0, "recall": 0.0},
                "validation": majority_metrics,
            },
            None,
        )
    )
    prevalence = float(train.y.mean())
    prevalence_probability = np.full(len(validation.y), prevalence)
    prevalence_threshold = select_threshold(validation.y, prevalence_probability)
    candidates.append(
        (
            {
                "model": "train_prevalence",
                "representation": "constant",
                "hyperparameters": {"trainPrevalence": prevalence},
                "complexity": "trivial",
                "selectedThreshold": prevalence_threshold,
                "validation": evaluate_probabilities(
                    validation.y, prevalence_probability, prevalence_threshold["threshold"]
                ),
            },
            None,
        )
    )

    for representation in ("flattened_sequence", "flattened_plus_source_summary"):
        preprocessor = fit_preprocessor(train, representation)
        train_values = preprocessor.transform(train)
        validation_values = preprocessor.transform(validation)
        names = feature_names(train, representation)
        for c_value in (0.01, 0.1, 1.0, 10.0):
            estimator = LogisticRegression(
                C=c_value,
                class_weight="balanced",
                max_iter=2000,
                random_state=SEED,
            ).fit(train_values, train.y)
            row = _evaluate_candidate(
                "logistic_regression",
                representation,
                estimator,
                validation_values,
                validation.y,
                {"C": c_value, "classWeight": "balanced"},
                "low",
            )
            candidates.append(
                (
                    row,
                    FrozenTemporalModel(
                        row["model"],
                        representation,
                        row["selectedThreshold"]["threshold"],
                        preprocessor,
                        estimator,
                        names,
                        file_sha256(MANIFEST_PATH),
                        SEED,
                    ),
                )
            )

        for n_estimators in (200, 400):
            for max_depth in (None, 5, 10):
                for min_samples_leaf in (1, 3, 5):
                    for weight in ("balanced", "balanced_subsample"):
                        estimator = RandomForestClassifier(
                            n_estimators=n_estimators,
                            max_depth=max_depth,
                            min_samples_leaf=min_samples_leaf,
                            class_weight=weight,
                            random_state=SEED,
                            n_jobs=1,
                        ).fit(train_values, train.y)
                        row = _evaluate_candidate(
                            "random_forest",
                            representation,
                            estimator,
                            validation_values,
                            validation.y,
                            {
                                "nEstimators": n_estimators,
                                "maxDepth": max_depth,
                                "minSamplesLeaf": min_samples_leaf,
                                "classWeight": weight,
                            },
                            "medium",
                        )
                        candidates.append(
                            (
                                row,
                                FrozenTemporalModel(
                                    row["model"],
                                    representation,
                                    row["selectedThreshold"]["threshold"],
                                    preprocessor,
                                    estimator,
                                    names,
                                    file_sha256(MANIFEST_PATH),
                                    SEED,
                                ),
                            )
                        )

    flat_preprocessor = fit_preprocessor(train, "flattened_sequence")
    flat_train = flat_preprocessor.transform(train)
    flat_validation = flat_preprocessor.transform(validation)
    flat_names = feature_names(train, "flattened_sequence")
    for architecture in ((32,), (64, 16)):
        estimator, training = _fit_mlp(flat_train, train.y, flat_validation, validation.y, architecture, 1e-3)
        row = _evaluate_candidate(
            "mlp",
            "flattened_sequence",
            estimator,
            flat_validation,
            validation.y,
            {"hiddenLayers": list(architecture), "alpha": 1e-3, "weightedBce": True},
            "medium",
            training,
        )
        candidates.append(
            (
                row,
                FrozenTemporalModel(
                    row["model"],
                    "flattened_sequence",
                    row["selectedThreshold"]["threshold"],
                    flat_preprocessor,
                    estimator,
                    flat_names,
                    file_sha256(MANIFEST_PATH),
                    SEED,
                ),
            )
        )

    sequence_preprocessor = fit_preprocessor(train, "ordered_sequence")
    sequence_train = sequence_preprocessor.transform(train)
    sequence_validation = sequence_preprocessor.transform(validation)
    for cell in ("gru", "lstm"):
        for hidden_size in (16, 32):
            estimator = NumpyRecurrentClassifier(
                cell, sequence_train.shape[-1], hidden_size, seed=SEED, learning_rate=0.01, l2=1e-4
            )
            training = estimator.fit(
                sequence_train,
                train.y,
                sequence_validation,
                validation.y,
                class_weights(train.y),
                max_epochs=250,
                patience=30,
            )
            row = _evaluate_candidate(
                cell.upper(),
                "ordered_sequence",
                estimator,
                sequence_validation,
                validation.y,
                {
                    "hiddenSize": hidden_size,
                    "layers": 1,
                    "learningRate": 0.01,
                    "l2": 1e-4,
                    "weightedBce": True,
                },
                "medium",
                {
                    "bestEpoch": training.best_epoch,
                    "epochsRun": training.epochs_run,
                    "bestValidationLogLoss": training.best_validation_loss,
                    "implementation": "deterministic NumPy full-batch BPTT",
                },
            )
            candidates.append(
                (
                    row,
                    FrozenTemporalModel(
                        row["model"],
                        "ordered_sequence",
                        row["selectedThreshold"]["threshold"],
                        sequence_preprocessor,
                        estimator,
                        feature_names(train, "ordered_sequence"),
                        file_sha256(MANIFEST_PATH),
                        SEED,
                    ),
                )
            )

    nontrivial = [(row, model) for row, model in candidates if model is not None]
    complexity_rank = {"low": 0, "medium": 1, "high": 2}
    selected_row, selected_model = max(
        nontrivial,
        key=lambda item: (
            item[0]["validation"]["prAuc"],
            item[0]["validation"]["f1"],
            -item[0]["validation"]["brier"],
            -complexity_rank[item[0]["complexity"]],
        ),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / "selected_model.joblib"
    save_frozen_model(artifact_path, selected_model)
    selection = {
        "experimentVersion": "temporal-hazard-phase2-v1",
        "randomSeed": SEED,
        "datasetVersion": manifest["datasetVersion"],
        "trainingManifestSha256": file_sha256(MANIFEST_PATH),
        "selectionData": ["train", "validation"],
        "testDataAccessed": False,
        "selectionPolicy": (
            "Highest validation PR-AUC, then F1, then lower Brier score, then lower complexity. "
            "Thresholds maximize validation F1 with recall/precision tie-breakers."
        ),
        "selectedModel": selected_row,
        "selectedArtifact": artifact_path.name,
    }
    selection["selectedArtifactSha256"] = file_sha256(artifact_path)
    save_json(output_dir / "candidate_results.json", [row for row, _ in candidates])
    save_json(output_dir / "model_selection.json", selection)
    return selection


def main() -> None:
    parser = argparse.ArgumentParser(description="Select a temporal-hazard candidate using train/validation only.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    args = parser.parse_args()
    print(json.dumps(run_selection(args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
