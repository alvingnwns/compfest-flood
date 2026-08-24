from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from dynamic_hazard.common import (  # noqa: E402
    MANIFEST_PATH,
    SEED,
    FrozenTemporalModel,
    SplitAccessError,
    evaluate_probabilities,
    feature_names,
    file_sha256,
    fit_preprocessor,
    load_frozen_model,
    load_selection_splits,
    load_split,
    save_frozen_model,
    select_threshold,
)
from dynamic_hazard.evaluate_selected_temporal_model import evaluate_frozen_test  # noqa: E402
from dynamic_hazard.recurrent import NumpyRecurrentClassifier  # noqa: E402
from dynamic_hazard.select_temporal_model import run_selection  # noqa: E402


def test_selection_loader_excludes_test_and_shapes_are_correct() -> None:
    train, validation = load_selection_splits()
    assert train.name == "train" and validation.name == "validation"
    assert train.X.shape[1:] == validation.X.shape[1:] == (30, 4)
    with pytest.raises(SplitAccessError):
        load_split("test")


def test_flattened_representation_and_train_only_scaler() -> None:
    train, validation = load_selection_splits()
    processor = fit_preprocessor(train, "flattened_sequence")
    transformed_train = processor.transform(train)
    transformed_validation = processor.transform(validation)
    assert transformed_train.shape == (len(train.X), 120)
    assert transformed_validation.shape == (len(validation.X), 120)
    assert np.allclose(processor.scaler.mean_, train.X.reshape(len(train.X), -1).mean(axis=0))


def test_preprocessor_rejects_non_train_fit() -> None:
    _, validation = load_selection_splits()
    with pytest.raises(ValueError, match="train split"):
        fit_preprocessor(validation, "flattened_sequence")


def test_threshold_and_metrics_use_supplied_validation_predictions() -> None:
    y = np.asarray([0, 0, 1, 1])
    probability = np.asarray([0.1, 0.4, 0.35, 0.8])
    selected = select_threshold(y, probability)
    metrics = evaluate_probabilities(y, probability, selected["threshold"])
    assert selected["f1"] == metrics["f1"]
    assert metrics["confusionMatrix"] == [[1, 1], [0, 2]]
    assert 0 <= metrics["prAuc"] <= 1


def test_probability_validation_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="within"):
        evaluate_probabilities(np.asarray([0, 1]), np.asarray([0.2, 1.2]), 0.5)


def test_logistic_reproducibility_and_serialization(tmp_path: Path) -> None:
    train, validation = load_selection_splits()
    processor = fit_preprocessor(train, "flattened_sequence")
    train_values = processor.transform(train)
    validation_values = processor.transform(validation)
    first = LogisticRegression(C=0.1, class_weight="balanced", max_iter=1000, random_state=SEED).fit(
        train_values, train.y
    )
    second = LogisticRegression(C=0.1, class_weight="balanced", max_iter=1000, random_state=SEED).fit(
        train_values, train.y
    )
    assert np.array_equal(first.predict_proba(validation_values), second.predict_proba(validation_values))
    threshold = select_threshold(validation.y, first.predict_proba(validation_values)[:, 1])["threshold"]
    frozen = FrozenTemporalModel(
        "logistic_regression",
        "flattened_sequence",
        threshold,
        processor,
        first,
        feature_names(train, "flattened_sequence"),
        file_sha256(MANIFEST_PATH),
        SEED,
    )
    path = tmp_path / "model.joblib"
    save_frozen_model(path, frozen)
    loaded = load_frozen_model(path)
    assert np.array_equal(frozen.predict_proba(validation), loaded.predict_proba(validation))
    assert hashlib.sha256(path.read_bytes()).hexdigest()
    assert isinstance(joblib.load(path), FrozenTemporalModel)


def test_recurrent_initialization_is_reproducible_and_probabilities_are_valid() -> None:
    train, _ = load_selection_splits()
    processor = fit_preprocessor(train, "ordered_sequence")
    values = processor.transform(train)[:5]
    for cell in ("gru", "lstm"):
        first = NumpyRecurrentClassifier(cell, input_size=4, hidden_size=4, seed=SEED)
        second = NumpyRecurrentClassifier(cell, input_size=4, hidden_size=4, seed=SEED)
        first_probability = first.predict_proba(values)
        second_probability = second.predict_proba(values)
        assert first_probability.shape == (5, 2)
        assert np.array_equal(first_probability, second_probability)
        assert ((first_probability >= 0) & (first_probability <= 1)).all()


def test_post_test_selection_and_repeated_evaluation_are_blocked(tmp_path: Path) -> None:
    (tmp_path / "test_evaluation.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="selection is frozen"):
        run_selection(tmp_path)
    with pytest.raises(RuntimeError, match="already exists"):
        evaluate_frozen_test(tmp_path)
