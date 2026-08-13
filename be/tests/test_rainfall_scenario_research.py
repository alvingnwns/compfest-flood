from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from dynamic_hazard.analyze_rainfall_scenarios import (  # noqa: E402
    PHASE2_DIR,
    SCORE_SEMANTICS,
    _cluster_candidates,
    analyze,
    derive_pattern_features,
)
from dynamic_hazard.common import file_sha256, load_selection_splits  # noqa: E402


def _hashes(directory: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


def test_descriptive_features_exclude_month_and_preserve_train_provenance() -> None:
    train, validation = load_selection_splits()
    train_features, names = derive_pattern_features(train)
    validation_features, validation_names = derive_pattern_features(validation)
    assert train_features.shape[0] == len(train.X)
    assert validation_features.shape[0] == len(validation.X)
    assert names == validation_names
    assert all("month" not in name.lower() for name in names)
    assert np.isfinite(train_features).all()


def test_clustering_is_deterministic_with_fixed_seed() -> None:
    train, _ = load_selection_splits()
    features, _ = derive_pattern_features(train)
    scaled = (features - features.mean(axis=0)) / features.std(axis=0)
    first_candidates, first_model, first_labels = _cluster_candidates(scaled)
    second_candidates, second_model, second_labels = _cluster_candidates(scaled)
    assert first_candidates == second_candidates
    assert first_model.n_clusters == second_model.n_clusters
    assert np.array_equal(first_labels, second_labels)


def test_research_artifacts_are_train_derived_relative_and_reproducible(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_report = analyze(first)
    second_report = analyze(second)
    assert first_report == second_report
    assert _hashes(first) == _hashes(second)
    assert first_report["trainOnlyDerived"] is True
    assert first_report["dataGovernance"]["testAccessed"] is False
    assert first_report["scoreSemantics"] == SCORE_SEMANTICS
    assert "probability" not in first_report["scoreSemantics"]
    selection = json.loads((PHASE2_DIR / "model_selection.json").read_text(encoding="utf-8"))
    artifact = PHASE2_DIR / selection["selectedArtifact"]
    assert first_report["phase2Model"]["sha256"] == file_sha256(artifact) == selection["selectedArtifactSha256"]
    assert first_report["phase2Model"]["retrained"] is False
    for representative in first_report["representatives"]:
        assert representative["sourceSplit"] == "train"
        assert 0 <= representative["temporalHazardScore"] <= 1
        assert representative["scoreSemantics"] == SCORE_SEMANTICS
    serialized = json.dumps(first_report).lower()
    assert "millimet" not in serialized and '"mm"' not in serialized
