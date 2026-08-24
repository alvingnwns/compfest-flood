from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from inspect_dynamic_hazard_dataset import (  # noqa: E402
    DEFAULT_ARCHIVE,
    SPLIT_FILES,
    inspect_archive,
    load_temporal_split,
)
from prepare_dynamic_hazard_dataset import prepare_dataset  # noqa: E402


def _hashes(directory: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


def test_archive_loads_and_expected_source_splits_exist() -> None:
    assert DEFAULT_ARCHIVE.is_file()
    with zipfile.ZipFile(DEFAULT_ARCHIVE) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
    assert all(f"Dataset_FloodRisk_Jakarta/{source}" in names for source in SPLIT_FILES.values())


def test_temporal_arrays_are_aligned_finite_and_binary() -> None:
    with zipfile.ZipFile(DEFAULT_ARCHIVE) as archive:
        for split in SPLIT_FILES:
            payload = load_temporal_split(archive, split)
            assert payload["X"].shape[0] == payload["y"].shape[0] == payload["dates"].shape[0]
            assert payload["X"].shape[1] == 30
            assert payload["X"].shape[2] == len(payload["stations"])
            assert set(np.unique(payload["y"])) == {0, 1}
            assert np.isfinite(payload["X"]).all()
            assert np.isfinite(payload["sum_feats"]).all()


def test_split_dates_and_sequences_are_disjoint_and_chronological() -> None:
    report = inspect_archive()
    assert report["splits"]["chronological"] is True
    assert report["splits"]["targetColumnInTemporalFeatures"] is False
    for details in report["temporal"].values():
        assert details["dates"]["sorted"] is True
        assert details["dates"]["duplicateCount"] == 0
        assert details["exactDuplicateSequencesWithinSplit"] == 0
    for pair in report["splits"]["pairs"].values():
        assert pair["sharedDates"] == []
        assert pair["exactDuplicateSequences"] == 0


def test_spatial_and_graph_findings_are_source_derived() -> None:
    report = inspect_archive()
    spatial = report["spatial"]
    graph = report["graph"]
    alignment = report["spatialGraphAlignment"]
    assert spatial["embeddingShape"][1] == len(spatial["embeddingDimensions"])
    assert spatial["uniqueNodeIds"] == spatial["embeddingShape"][0]
    assert graph["metadata"]["counts"]["N"] == graph["uniqueNodeIds"]
    assert len(alignment["matchedIds"]) == spatial["uniqueNodeIds"]
    assert alignment["unmatchedSpatialIds"] == []
    assert len(alignment["unmatchedGraphIds"]) == graph["uniqueNodeIds"] - spatial["uniqueNodeIds"]


def test_raw_graph_detection_and_static_embedding_result_are_reproducible() -> None:
    first = inspect_archive()["graph"]
    second = inspect_archive()["graph"]
    assert first["rawGraphAvailable"] is False
    assert first["rawGraphCandidates"] == []
    assert first["totalEmbeddingRows"] == sum(shape[0] for shape in first["embeddingShapes"].values())
    assert first["uniqueEmbeddingRows"] == second["uniqueEmbeddingRows"] == 1
    assert first["embeddingsVaryAcrossSamples"] is False
    assert first["variancePerDimension"] == second["variancePerDimension"]


def test_manifest_matches_canonical_processed_arrays(tmp_path: Path) -> None:
    output = tmp_path / "processed"
    manifest = prepare_dataset(
        output_dir=output,
        processing_timestamp="2026-08-13T00:00:00Z",
    )
    persisted = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert persisted == manifest
    assert manifest["archiveSha256"] == hashlib.sha256(DEFAULT_ARCHIVE.read_bytes()).hexdigest()
    assert manifest["sequenceLength"] == 30
    assert manifest["rawGraphAvailable"] is False
    for split, expected_count in manifest["sampleCounts"].items():
        with np.load(output / f"temporal_{split}.npz", allow_pickle=False) as payload:
            assert len(payload["X"]) == len(payload["y"]) == len(payload["dates"]) == expected_count
            assert payload["dates"].dtype.kind == "U"
            assert payload["X"].shape[1:] == (30, len(manifest["featureNames"]))


def test_processed_generation_is_deterministic_with_fixed_provenance_time(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    timestamp = "2026-08-13T00:00:00Z"
    prepare_dataset(output_dir=first, processing_timestamp=timestamp)
    prepare_dataset(output_dir=second, processing_timestamp=timestamp)
    assert _hashes(first) == _hashes(second)
