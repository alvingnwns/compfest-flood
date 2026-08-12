import csv
import json
from pathlib import Path

from scripts.run_global_flood_feasibility_gate import evaluate

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "app" / "data"


def test_global_flood_discovery_preserves_source_semantics() -> None:
    discovery = json.loads((DATA_DIR / "global-flood-db" / "event-discovery.json").read_text(encoding="utf-8"))
    metadata = discovery["metadata"]
    assert metadata["collectionId"] == "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1"
    assert metadata["effectiveSourceResolutionMeters"] == 250
    assert metadata["earthEngineNominalScaleMeters"] == 250
    assert metadata["targetDefinition"].startswith("roadCorridorFloodExposure")
    assert discovery["summary"]["eventsWithDetectedNonPermanentFloodInPilot"] == 2


def test_corridor_labels_reuse_osm_ids_and_preserve_unknowns() -> None:
    with (DATA_DIR / "datasets" / "global_flood_road_corridor_labels.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    roads = json.loads((DATA_DIR / "roads" / "jakarta-2025-03-04-road-features.geojson").read_text(encoding="utf-8"))
    segment_ids = {feature["properties"]["segmentId"] for feature in roads["features"]}
    assert len(rows) == 2 * len(segment_ids)
    assert {row["segment_id"] for row in rows} == segment_ids
    remote_event = [row for row in rows if row["event_context_confidence"] == "low"]
    assert remote_event
    assert {row["label"] for row in remote_event} == {"unknown"}
    assert {row["exclusion_reason"] for row in remote_event} == {"event_context_not_jakarta"}


def test_sensitivity_does_not_promote_unstable_candidate_to_canonical_positive() -> None:
    sensitivity = json.loads((DATA_DIR / "global-flood-db" / "corridor-sensitivity.json").read_text(encoding="utf-8"))
    canonical = sensitivity["canonical"]
    assert canonical["positive"] == 0
    assert any(configuration["positive"] > 0 for configuration in sensitivity["configurations"])
    assert canonical["name"] == "canonical"
    assert canonical["bufferRadiusMeters"] == 250


def test_jakarta_fallback_gate_stays_failed_after_multiregion_runtime_activation() -> None:
    result = evaluate()
    assert result["status"] == "FAIL"
    assert result["finalRealHistoricalMlFeasibility"] == "FAIL"
    assert not result["checks"]["multipleIndependentHistoricalEvents"]["passed"]
    assert not result["checks"]["multiplePositiveEventGroups"]["passed"]
    assert not result["checks"]["eventTemporalSplitPossible"]["passed"]
    assert result["activeRuntimeTrainingData"] == "real-historical-global-flood-database-indonesia"
    assert result["statistics"]["march2025Role"] == "demo_only_not_a_global_flood_database_evaluation_event"


def test_previous_sentinel_failure_remains_documented() -> None:
    gate = json.loads((DATA_DIR / "flood-events" / "scientific-feasibility-gate.json").read_text(encoding="utf-8"))
    assert gate["status"] == "FAIL"
    assert gate["statistics"]["positive"] == 0
