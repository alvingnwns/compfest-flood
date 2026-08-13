from __future__ import annotations

import argparse
import hashlib
import io
import json
import pickletools
import re
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ARCHIVE = BASE_DIR / "data" / "dynamic-hazard" / "raw" / "Dataset_FloodRisk_Jakarta.zip"
ARCHIVE_ROOT = "Dataset_FloodRisk_Jakarta/"
SCRIPT_VERSION = "1.0.0"
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
SPLIT_FILES = {
    "train": "temporal_artifacts/windows_T30_H3_stride5_train_ds.npz",
    "validation": "temporal_artifacts/windows_T30_H3_stride5_val.npz",
    "test": "temporal_artifacts/windows_T30_H3_stride5_test.npz",
}
GRAPH_EMBEDDING_FILES = {
    "train": "graph_artifacts/gnn_concat_T30_H3_train.npy",
    "validation": "graph_artifacts/gnn_concat_T30_H3_val.npy",
    "test": "graph_artifacts/gnn_concat_T30_H3_test.npy",
}
SPATIAL_FILE = "spatial_artifacts/patch_emb_64d.csv"
NODE_POSITION_FILE = "graph_artifacts/gnn_node_positions.csv"
GRAPH_METADATA_FILE = "graph_artifacts/pyg_graph_directed_meta.json"
SUSPICIOUS_SENTINELS = (-9999.0, -999.0, -99.0, 999.0, 9999.0)


def archive_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_npy(payload: bytes) -> np.ndarray:
    return np.load(io.BytesIO(payload), allow_pickle=False)


def _read_npz_member(archive: zipfile.ZipFile, source_name: str, member: str) -> np.ndarray:
    with zipfile.ZipFile(io.BytesIO(archive.read(ARCHIVE_ROOT + source_name))) as nested:
        return _read_npy(nested.read(f"{member}.npy"))


def _read_dates(archive: zipfile.ZipFile, source_name: str) -> np.ndarray:
    """Read ISO date strings from the source object array without executing its pickle.

    The released dates arrays use NumPy object dtype. Loading those arrays with
    allow_pickle=True would execute a pickle supplied by the archive. Instead, this
    parser reads only pickle string opcodes and accepts exactly one ISO date per row.
    """
    with zipfile.ZipFile(io.BytesIO(archive.read(ARCHIVE_ROOT + source_name))) as nested:  # noqa: SIM117
        with nested.open("dates.npy") as source:
            version = np.lib.format.read_magic(source)
            reader = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
            shape, _, dtype = reader(source)
            if len(shape) != 1 or not dtype.hasobject:
                raise ValueError(f"Unexpected dates.npy schema in {source_name}: shape={shape}, dtype={dtype}")
            strings = [
                argument
                for opcode, argument, _ in pickletools.genops(source.read())
                if opcode.name in {"UNICODE", "BINUNICODE", "SHORT_BINUNICODE"}
                and isinstance(argument, str)
                and DATE_PATTERN.fullmatch(argument)
            ]
    if len(strings) != shape[0] or len(strings) != len(set(strings)):
        raise ValueError(f"Could not safely recover one unique ISO date per row from {source_name}")
    for value in strings:
        date.fromisoformat(value)
    return np.asarray(strings, dtype="U10")


def load_temporal_split(archive: zipfile.ZipFile, split: str) -> dict[str, np.ndarray]:
    source_name = SPLIT_FILES[split]
    return {
        "X": _read_npz_member(archive, source_name, "X"),
        "y": _read_npz_member(archive, source_name, "y"),
        "dates": _read_dates(archive, source_name),
        "stations": _read_npz_member(archive, source_name, "stations"),
        "sum_feats": _read_npz_member(archive, source_name, "sum_feats"),
        "sum_names": _read_npz_member(archive, source_name, "sum_names"),
    }


def _row_hashes(values: np.ndarray) -> set[str]:
    return {hashlib.sha256(np.ascontiguousarray(row).tobytes()).hexdigest() for row in values}


def _maximum_sequence_overlap(left: np.ndarray, right: np.ndarray) -> int:
    maximum = min(len(left), len(right)) - 1
    for steps in range(maximum, 0, -1):
        if np.array_equal(left[-steps:], right[:steps]):
            return steps
    return 0


def _adjacent_overlap_distribution(values: np.ndarray) -> dict[str, int]:
    overlaps = [_maximum_sequence_overlap(values[index], values[index + 1]) for index in range(len(values) - 1)]
    return {str(key): value for key, value in sorted(Counter(overlaps).items())}


def _date_gap_distribution(values: np.ndarray) -> dict[str, int]:
    parsed = [date.fromisoformat(str(value)) for value in values]
    gaps = [(right - left).days for left, right in zip(parsed, parsed[1:], strict=False)]
    return {str(key): value for key, value in sorted(Counter(gaps).items())}


def _numeric_summary(values: np.ndarray) -> dict[str, Any]:
    return {
        "shape": list(values.shape),
        "dtype": str(values.dtype),
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
        "missingValues": int(np.isnan(values).sum()),
        "infinities": int(np.isinf(values).sum()),
        "suspiciousSentinelCounts": {
            str(sentinel): int(np.count_nonzero(values == sentinel))
            for sentinel in SUSPICIOUS_SENTINELS
            if np.any(values == sentinel)
        },
    }


def _raw_graph_candidates(archive: zipfile.ZipFile) -> list[str]:
    candidates: list[str] = []
    patterns = (
        re.compile(r"(^|[/_-])edge[_-]?index([._/-]|$)"),
        re.compile(r"(^|[/_-])edge[_-]?list([._/-]|$)"),
        re.compile(r"(^|[/_-])edges?\.(csv|npy|npz|json|parquet)$"),
        re.compile(r"(^|[/_-])adj(acency)?([._/-]|$)"),
        re.compile(r"(^|[/_-])(source|src)[_-](target|dst)([._/-]|$)"),
        re.compile(r"\.(graphml|gml|gexf|gpickle|pt|pth)$"),
    )
    for name in archive.namelist():
        lowered = name.lower()
        if any(pattern.search(lowered) for pattern in patterns):
            candidates.append(name)
        if name.endswith(".npz"):
            with zipfile.ZipFile(io.BytesIO(archive.read(name))) as nested:
                for member in nested.namelist():
                    qualified = f"{name}!{member}"
                    if any(pattern.search(member.lower()) for pattern in patterns):
                        candidates.append(qualified)
    return sorted(set(candidates))


def inspect_archive(path: Path = DEFAULT_ARCHIVE) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Dataset archive not found: {path}")

    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise ValueError(f"Archive CRC validation failed for {bad_member}")
        files = [entry for entry in archive.infolist() if not entry.is_dir()]
        temporal = {split: load_temporal_split(archive, split) for split in SPLIT_FILES}

        temporal_report: dict[str, Any] = {}
        for split, payload in temporal.items():
            values = payload["X"]
            targets = payload["y"]
            dates = payload["dates"]
            channel_summaries = []
            for index, name in enumerate(payload["stations"].tolist()):
                summary = _numeric_summary(values[:, :, index])
                summary["name"] = str(name)
                channel_summaries.append(summary)
            classes, counts = np.unique(targets, return_counts=True)
            temporal_report[split] = {
                "sourceFile": SPLIT_FILES[split],
                "X": _numeric_summary(values),
                "y": {"shape": list(targets.shape), "dtype": str(targets.dtype)},
                "dates": {
                    "shape": list(dates.shape),
                    "dtype": str(dates.dtype),
                    "earliest": str(dates[0]),
                    "latest": str(dates[-1]),
                    "sorted": bool(np.all(dates[:-1] < dates[1:])),
                    "duplicateCount": int(len(dates) - len(set(dates.tolist()))),
                    "gapDaysDistribution": _date_gap_distribution(dates),
                },
                "sampleCount": int(len(values)),
                "sequenceLength": int(values.shape[1]),
                "channelCount": int(values.shape[2]),
                "featureNames": [str(item) for item in payload["stations"].tolist()],
                "channelSummaries": channel_summaries,
                "summaryFeatures": {
                    **_numeric_summary(payload["sum_feats"]),
                    "names": [str(item) for item in payload["sum_names"].tolist()],
                },
                "target": {
                    "uniqueValues": [int(item) for item in classes.tolist()],
                    "classCounts": {str(int(key)): int(value) for key, value in zip(classes, counts, strict=True)},
                    "positiveRatio": float(np.mean(targets == 1)),
                },
                "exactDuplicateSequencesWithinSplit": int(len(values) - len(_row_hashes(values))),
                "adjacentWindowOverlapSteps": _adjacent_overlap_distribution(values),
            }

        split_pairs: dict[str, Any] = {}
        split_names = list(SPLIT_FILES)
        for index, left_name in enumerate(split_names):
            for right_name in split_names[index + 1 :]:
                left = temporal[left_name]
                right = temporal[right_name]
                pair_name = f"{left_name}-{right_name}"
                split_pairs[pair_name] = {
                    "sharedDates": sorted(set(left["dates"].tolist()) & set(right["dates"].tolist())),
                    "exactDuplicateSequences": len(_row_hashes(left["X"]) & _row_hashes(right["X"])),
                    "boundaryWindowOverlapSteps": _maximum_sequence_overlap(left["X"][-1], right["X"][0]),
                }

        spatial = pd.read_csv(io.BytesIO(archive.read(ARCHIVE_ROOT + SPATIAL_FILE)))
        positions = pd.read_csv(io.BytesIO(archive.read(ARCHIVE_ROOT + NODE_POSITION_FILE)))
        spatial_ids = set(spatial["node_id"].astype(int))
        position_ids = set(positions["node_id"].astype(int))
        spatial_values = spatial.drop(columns="node_id")
        position_values = positions.drop(columns="node_id")

        graph_embeddings = {
            split: _read_npy(archive.read(ARCHIVE_ROOT + source_name))
            for split, source_name in GRAPH_EMBEDDING_FILES.items()
        }
        all_graph_embeddings = np.concatenate(list(graph_embeddings.values()))
        graph_metadata = json.loads(archive.read(ARCHIVE_ROOT + GRAPH_METADATA_FILE))
        raw_graph_candidates = _raw_graph_candidates(archive)

    feature_names = temporal["train"]["stations"].tolist()
    return {
        "archive": {
            "filename": path.name,
            "sha256": archive_sha256(path),
            "totalEntries": len(files),
            "filenames": [entry.filename for entry in files],
            "formats": dict(Counter(Path(entry.filename).suffix.lower() for entry in files)),
        },
        "temporal": temporal_report,
        "splits": {
            "chronological": bool(
                temporal["train"]["dates"][-1] < temporal["validation"]["dates"][0]
                and temporal["validation"]["dates"][-1] < temporal["test"]["dates"][0]
            ),
            "pairs": split_pairs,
            "targetColumnInTemporalFeatures": any(
                str(name).lower() in {"y", "target", "flood", "flood_target"} for name in feature_names
            ),
            "futureObservationAudit": {
                "verifiable": False,
                "reason": (
                    "The released archive provides reference-date strings but no per-timestep observation dates or "
                    "window-alignment metadata; future-rainfall exclusion cannot be independently proven."
                ),
            },
        },
        "spatial": {
            "sourceFile": SPATIAL_FILE,
            "shape": list(spatial.shape),
            "embeddingShape": [int(len(spatial)), int(len(spatial_values.columns))],
            "embeddingDimensions": [str(column) for column in spatial_values.columns],
            "uniqueNodeIds": int(spatial["node_id"].nunique()),
            "duplicateNodeIds": int(spatial["node_id"].duplicated().sum()),
            "uniqueEmbeddingRows": int(spatial_values.drop_duplicates().shape[0]),
            "duplicateEmbeddingRows": int(len(spatial_values) - len(spatial_values.drop_duplicates())),
            "missingValues": int(spatial.isna().sum().sum()),
            "infinities": int(np.isinf(spatial.select_dtypes(include=[np.number])).sum().sum()),
        },
        "graph": {
            "nodePositionSourceFile": NODE_POSITION_FILE,
            "nodePositionShape": list(positions.shape),
            "nodePositionColumns": [str(column) for column in positions.columns],
            "uniqueNodeIds": int(positions["node_id"].nunique()),
            "duplicateNodeIds": int(positions["node_id"].duplicated().sum()),
            "uniqueCoordinateRows": int(position_values.drop_duplicates().shape[0]),
            "missingValues": int(positions.isna().sum().sum()),
            "infinities": int(np.isinf(positions.select_dtypes(include=[np.number])).sum().sum()),
            "metadata": graph_metadata,
            "embeddingShapes": {split: list(values.shape) for split, values in graph_embeddings.items()},
            "totalEmbeddingRows": int(len(all_graph_embeddings)),
            "uniqueEmbeddingRows": int(np.unique(all_graph_embeddings, axis=0).shape[0]),
            "variancePerDimension": np.var(all_graph_embeddings.astype(np.float64), axis=0).tolist(),
            "embeddingsVaryAcrossSamples": bool(np.unique(all_graph_embeddings, axis=0).shape[0] > 1),
            "rawGraphCandidates": raw_graph_candidates,
            "rawGraphAvailable": bool(raw_graph_candidates),
        },
        "spatialGraphAlignment": {
            "matchedIds": sorted(spatial_ids & position_ids),
            "unmatchedSpatialIds": sorted(spatial_ids - position_ids),
            "unmatchedGraphIds": sorted(position_ids - spatial_ids),
        },
    }


def format_report(report: dict[str, Any]) -> str:
    lines = [
        "DYNAMIC HAZARD DATASET INSPECTION",
        "",
        "ARCHIVE",
        f"filename: {report['archive']['filename']}",
        f"SHA-256: {report['archive']['sha256']}",
        f"files: {report['archive']['totalEntries']}",
        f"formats: {json.dumps(report['archive']['formats'], sort_keys=True)}",
    ]
    lines.extend(f"- {name}" for name in report["archive"]["filenames"])
    lines.extend(["", "TEMPORAL DATA"])
    for split, details in report["temporal"].items():
        lines.append(
            f"{split}: X={details['X']['shape']} {details['X']['dtype']}; "
            f"y={details['y']['shape']}; dates={details['dates']['earliest']}..{details['dates']['latest']}; "
            f"classes={details['target']['classCounts']}"
        )
        lines.append(
            f"  features={details['featureNames']}; NaN={details['X']['missingValues']}; "
            f"Inf={details['X']['infinities']}; adjacent-overlap={details['adjacentWindowOverlapSteps']}"
        )
    lines.extend(
        [
            "",
            "SPLIT / LEAKAGE AUDIT",
            f"chronological: {report['splits']['chronological']}",
            f"target column in temporal features: {report['splits']['targetColumnInTemporalFeatures']}",
            f"pair checks: {json.dumps(report['splits']['pairs'], sort_keys=True)}",
            f"future observation audit: {json.dumps(report['splits']['futureObservationAudit'], sort_keys=True)}",
            "",
            "SPATIAL EMBEDDINGS",
            f"shape: {report['spatial']['embeddingShape']}",
            f"unique IDs: {report['spatial']['uniqueNodeIds']}; duplicate IDs: {report['spatial']['duplicateNodeIds']}",
            f"unique embedding rows: {report['spatial']['uniqueEmbeddingRows']}",
            "",
            "GRAPH DATA",
            f"node positions: {report['graph']['nodePositionShape']}",
            f"metadata: {json.dumps(report['graph']['metadata'], sort_keys=True)}",
            f"embedding shapes: {json.dumps(report['graph']['embeddingShapes'], sort_keys=True)}",
            f"total embedding rows: {report['graph']['totalEmbeddingRows']}",
            f"unique embedding rows: {report['graph']['uniqueEmbeddingRows']}",
            f"embeddings vary across samples: {report['graph']['embeddingsVaryAcrossSamples']}",
            f"RAW_GRAPH_AVAILABLE = {str(report['graph']['rawGraphAvailable']).lower()}",
            "",
            "SPATIAL / GRAPH ID ALIGNMENT",
            f"matched IDs: {len(report['spatialGraphAlignment']['matchedIds'])}",
            f"unmatched spatial IDs: {report['spatialGraphAlignment']['unmatchedSpatialIds']}",
            f"unmatched graph IDs: {report['spatialGraphAlignment']['unmatchedGraphIds']}",
        ]
    )
    if not report["graph"]["embeddingsVaryAcrossSamples"]:
        lines.extend(
            [
                "",
                "FINDING: The released graph representation is static across temporal samples and therefore does "
                "not provide sample-specific dynamic spatial flood state.",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely inspect the released Jakarta dynamic-hazard dataset.")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--json", action="store_true", help="Print the complete machine-readable audit as JSON.")
    args = parser.parse_args()
    report = inspect_archive(args.archive)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else format_report(report))


if __name__ == "__main__":
    main()
