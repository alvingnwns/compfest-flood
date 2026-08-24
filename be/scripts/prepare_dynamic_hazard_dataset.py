from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from inspect_dynamic_hazard_dataset import (
    DEFAULT_ARCHIVE,
    SCRIPT_VERSION,
    SPLIT_FILES,
    inspect_archive,
    load_temporal_split,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "dynamic-hazard" / "processed"
CANONICAL_DATASET_VERSION = "jakarta-dynamic-hazard-temporal-v1"
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _npy_bytes(values: np.ndarray) -> bytes:
    output = io.BytesIO()
    np.lib.format.write_array(output, np.asarray(values), allow_pickle=False)
    return output.getvalue()


def _write_deterministic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for name in sorted(arrays):
            info = zipfile.ZipInfo(f"{name}.npy", FIXED_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            target.writestr(info, _npy_bytes(arrays[name]), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    temporary.replace(path)


def _processing_timestamp(explicit: str | None) -> str:
    if explicit:
        parsed = datetime.fromisoformat(explicit.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("--processing-timestamp must include a UTC offset")
        return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if epoch := os.getenv("SOURCE_DATE_EPOCH"):
        return datetime.fromtimestamp(int(epoch), tz=UTC).isoformat().replace("+00:00", "Z")
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _validate_for_processing(report: dict[str, Any]) -> None:
    failures = []
    if not report["splits"]["chronological"]:
        failures.append("splits are not chronological")
    if report["splits"]["targetColumnInTemporalFeatures"]:
        failures.append("target-like field appears in temporal feature names")
    for split, details in report["temporal"].items():
        if (
            details["X"]["shape"][0] != details["y"]["shape"][0]
            or details["X"]["shape"][0] != details["dates"]["shape"][0]
        ):
            failures.append(f"{split} arrays are not row-aligned")
        if details["sequenceLength"] != 30:
            failures.append(f"{split} sequence length is not 30")
        if details["target"]["uniqueValues"] != [0, 1]:
            failures.append(f"{split} target is not binary")
        if details["X"]["missingValues"] or details["X"]["infinities"]:
            failures.append(f"{split} temporal tensor contains non-finite values")
    for pair, details in report["splits"]["pairs"].items():
        if details["sharedDates"] or details["exactDuplicateSequences"]:
            failures.append(f"{pair} shares dates or exact temporal sequences")
    if failures:
        raise ValueError("Dataset validation failed: " + "; ".join(failures))


def prepare_dataset(
    archive_path: Path = DEFAULT_ARCHIVE,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    processing_timestamp: str | None = None,
) -> dict[str, Any]:
    report = inspect_archive(archive_path)
    _validate_for_processing(report)
    output_dir.mkdir(parents=True, exist_ok=True)

    processed_files: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(archive_path) as archive:
        for split in SPLIT_FILES:
            payload = load_temporal_split(archive, split)
            output_path = output_dir / f"temporal_{split}.npz"
            _write_deterministic_npz(output_path, payload)
            processed_files[output_path.name] = {
                "sha256": _sha256(output_path),
                "sampleCount": int(len(payload["X"])),
            }

    class_distribution = {split: details["target"]["classCounts"] for split, details in report["temporal"].items()}
    manifest = {
        "datasetVersion": CANONICAL_DATASET_VERSION,
        "sourceDatasetVersion": "not provided",
        "datasetName": "Processed Flood Risk Prediction Dataset for Jakarta",
        "sourceFilename": archive_path.name,
        "archiveSha256": report["archive"]["sha256"],
        "processingTimestamp": _processing_timestamp(processing_timestamp),
        "processingScript": "scripts/prepare_dynamic_hazard_dataset.py",
        "processingScriptVersion": SCRIPT_VERSION,
        "sourceFilesUsed": [SPLIT_FILES[split] for split in SPLIT_FILES],
        "sampleCounts": {split: details["sampleCount"] for split, details in report["temporal"].items()},
        "dateRanges": {
            split: {"earliest": details["dates"]["earliest"], "latest": details["dates"]["latest"]}
            for split, details in report["temporal"].items()
        },
        "splitDefinition": {
            "train": "source-provided split; reference dates 2014-2018",
            "validation": "source-provided split; reference dates 2019",
            "test": "source-provided split; reference dates 2020",
        },
        "sequenceLength": report["temporal"]["train"]["sequenceLength"],
        "featureNames": report["temporal"]["train"]["featureNames"],
        "featureRepresentation": (
            "source-provided transformed/scaled temporal values; physical rainfall units and transform parameters "
            "are not documented in the released dataset"
        ),
        "summaryFeatureNames": report["temporal"]["train"]["summaryFeatures"]["names"],
        "targetDefinition": "binary flood target as provided by source dataset",
        "targetSemantics": "binary flood target as provided by source dataset",
        "groundTruthSource": "not documented in released dataset",
        "classDistribution": class_distribution,
        "spatialEmbeddingShape": report["spatial"]["embeddingShape"],
        "graphNodeCount": report["graph"]["metadata"]["counts"]["N"],
        "graphMetadataEdgeCount": report["graph"]["metadata"]["counts"]["E"],
        "graphEmbeddingShapes": report["graph"]["embeddingShapes"],
        "graphEmbeddingUniqueRows": report["graph"]["uniqueEmbeddingRows"],
        "rawGraphAvailable": report["graph"]["rawGraphAvailable"],
        "canonicalSampleSchema": {
            "referenceDate": "ISO-8601 date string copied from source dates array",
            "rainfallSequence": "30 x 4 source-preserved temporal tensor",
            "target": "0 or 1",
            "split": "train, validation, or test",
        },
        "processedFiles": processed_files,
        "knownLimitations": [
            "Target ground-truth provenance is not documented in the released dataset.",
            "Temporal station channels are transformed/scaled; raw rainfall units and transform parameters are absent.",
            "Per-timestep observation dates are absent, so future-rainfall exclusion cannot be independently proven.",
            "The released graph representation is static across temporal samples and therefore does not provide sample-specific dynamic spatial flood state.",  # noqa: E501
            "Graph metadata reports node/edge counts, but no raw edge list, edge_index, adjacency matrix, or graph object is released.",  # noqa: E501
            "Spatial embeddings cover 314 IDs while node positions cover 384 IDs; no mapping to Jakarta OSM road segments is provided.",  # noqa: E501
        ],
    }
    manifest_path = output_dir / "manifest.json"
    temporary_manifest = manifest_path.with_suffix(".json.tmp")
    temporary_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary_manifest.replace(manifest_path)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare canonical temporal arrays from the Jakarta dataset archive.")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--processing-timestamp",
        help="Optional ISO-8601 timestamp for reproducible manifests; SOURCE_DATE_EPOCH is also supported.",
    )
    args = parser.parse_args()
    manifest = prepare_dataset(args.archive, args.output_dir, processing_timestamp=args.processing_timestamp)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
