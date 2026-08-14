from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np

from app.errors import ApiError

APP_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = APP_DIR / "data" / "dynamic-hazard" / "runtime"
SCENARIO_PATH = RUNTIME_DIR / "rainfall_scenarios.json"
SEQUENCE_PATH = RUNTIME_DIR / "representative_sequences.npz"


@dataclass(frozen=True)
class RainfallScenario:
    id: str
    representative_sequence: np.ndarray
    reference_date: str
    source_sample_index: int
    temporal_hazard_score_research: float
    research_group_median_temporal_hazard_score: float
    relative_hazard_index: float
    provenance: Mapping[str, Any]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def _load_scenarios() -> Mapping[str, RainfallScenario]:
    try:
        manifest = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        expected_archive_hash = manifest["sourceSequenceArtifactSha256"]
        if _file_sha256(SEQUENCE_PATH) != expected_archive_hash:
            raise ValueError("representative sequence artifact hash mismatch")
        scenarios: dict[str, RainfallScenario] = {}
        with np.load(SEQUENCE_PATH, allow_pickle=False) as sequences:
            for record in manifest["scenarios"]:
                sequence = np.asarray(sequences[record["sequenceKey"]], dtype=np.float64)
                if sequence.shape != (30, 4) or not np.isfinite(sequence).all():
                    raise ValueError(f"invalid representative sequence for {record['id']}")
                if hashlib.sha256(sequence.tobytes(order="C")).hexdigest() != record["sequenceSha256"]:
                    raise ValueError(f"representative sequence hash mismatch for {record['id']}")
                sequence.setflags(write=False)
                provenance = MappingProxyType(
                    {
                        "sourceExperiment": manifest["sourceExperiment"],
                        "sourceSplit": manifest["sourceSplit"],
                        "sourceSampleIndex": int(record["sourceSampleIndex"]),
                        "sequenceSha256": record["sequenceSha256"],
                        "probabilityCalibrated": False,
                    }
                )
                scenarios[record["id"]] = RainfallScenario(
                    id=record["id"],
                    representative_sequence=sequence,
                    reference_date=record["referenceDate"],
                    source_sample_index=int(record["sourceSampleIndex"]),
                    temporal_hazard_score_research=float(record["representativeTemporalHazardScore"]),
                    research_group_median_temporal_hazard_score=float(record["researchGroupMedianTemporalHazardScore"]),
                    relative_hazard_index=float(record["relativeHazardIndex"]),
                    provenance=provenance,
                )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ApiError(
            500,
            "DYNAMIC_HAZARD_RUNTIME_ERROR",
            "Artefak skenario hujan runtime tidak valid.",
            details={"component": "rainfall_scenarios"},
        ) from exc
    if set(scenarios) != {"Q1", "Q2", "Q3", "Q4"}:
        raise ApiError(500, "DYNAMIC_HAZARD_RUNTIME_ERROR", "Set skenario hujan runtime tidak lengkap.")
    return MappingProxyType(scenarios)


def get_rainfall_scenario(scenario_id: str) -> RainfallScenario:
    scenario = _load_scenarios().get(scenario_id)
    if scenario is None:
        raise ApiError(
            422,
            "UNKNOWN_RAINFALL_SCENARIO",
            "Skenario hujan tidak dikenal.",
            details={"rainfallScenario": scenario_id, "supported": ["Q1", "Q2", "Q3", "Q4"]},
        )
    return scenario


def list_rainfall_scenarios() -> tuple[RainfallScenario, ...]:
    scenarios = _load_scenarios()
    return tuple(scenarios[key] for key in ("Q1", "Q2", "Q3", "Q4"))
