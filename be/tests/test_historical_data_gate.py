import csv
import json
from pathlib import Path

from scripts.run_scientific_feasibility_gate import evaluate

BASE_DIR = Path(__file__).resolve().parents[1]


def test_event_roles_are_temporal_and_march_2025_is_holdout() -> None:
    catalogue = json.loads(
        (BASE_DIR / "app" / "data" / "flood-events" / "jakarta-events.json").read_text(encoding="utf-8")
    )
    events = catalogue["events"]
    holdout = [event for event in events if event["role"] == "holdout"]
    assert len(events) == 4
    assert len(holdout) == 1
    assert holdout[0]["eventId"] == "jakarta-20250304"
    assert all(event["sourceName"] in {"BPBD DKI Jakarta", "BNPB"} for event in events)


def test_road_labels_preserve_unknown_and_never_force_uncovered_events_negative() -> None:
    labels_path = BASE_DIR / "app" / "data" / "datasets" / "historical_road_flood_labels.csv"
    with labels_path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    excluded = [row for row in rows if row["event_id"] in {"jakarta-20220118", "jakarta-20250304"}]
    assert excluded
    assert {row["label"] for row in excluded} == {"unknown"}
    assert all(row["exclusion_reason"] for row in excluded)


def test_scientific_gate_fails_before_training_and_runtime_artifact_stays_synthetic() -> None:
    result = evaluate()
    assert result["status"] == "FAIL"
    assert result["statistics"]["positive"] == 0
    assert not result["checks"]["meaningfulClassSupport"]
    metrics = json.loads((BASE_DIR / "app" / "models" / "flood_risk_metrics.json").read_text(encoding="utf-8"))
    assert metrics["trainingData"] == "synthetic"
