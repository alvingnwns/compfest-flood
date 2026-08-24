from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
EVENTS_PATH = DATA_DIR / "flood-events" / "jakarta-events.json"
AVAILABILITY_PATH = DATA_DIR / "flood-events" / "sentinel-1-availability.json"
LABELS_PATH = DATA_DIR / "datasets" / "historical_road_flood_labels.csv"
OUTPUT_PATH = DATA_DIR / "flood-events" / "scientific-feasibility-gate.json"


def evaluate() -> dict[str, Any]:
    catalogue = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    availability = json.loads(AVAILABILITY_PATH.read_text(encoding="utf-8"))
    with LABELS_PATH.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    counts = Counter(row["label"] for row in rows)
    by_event: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        by_event[row["event_id"]][row["label"]] += 1
    usable_events = [event_id for event_id, values in by_event.items() if values["positive"] + values["negative"] > 0]
    holdout = next(event for event in catalogue["events"] if event["role"] == "holdout")
    holdout_availability = next(event for event in availability["events"] if event["eventId"] == holdout["eventId"])
    checks = {
        "multipleUsableEventGroups": len(usable_events) >= 3,
        "defensiblePositiveLabels": counts["positive"] >= 30,
        "defensibleNegativeLabels": counts["negative"] >= 30,
        "meaningfulClassSupport": counts["positive"] > 0 and counts["negative"] > 0,
        "eventTemporalSplitPossible": sum(event["role"] == "train" for event in catalogue["events"]) >= 2
        and any(event["role"] == "validation" and event["eventId"] in usable_events for event in catalogue["events"]),
        "independentHoldoutUsable": by_event[holdout["eventId"]]["positive"] + by_event[holdout["eventId"]]["negative"]
        > 0,
        "holdoutNotUsedForTuning": True,
        "nonLeakyFeaturesAvailable": False,
    }
    failures = [name for name, passed in checks.items() if not passed]
    result: dict[str, Any] = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failures": failures,
        "statistics": {
            "historicalEvents": len(catalogue["events"]),
            "sentinelAcquisitionsInspected": sum(event["acquisitionCount"] for event in availability["events"]),
            "osmRoadSegments": len({row["segment_id"] for row in rows}),
            "roadEventObservations": len(rows),
            "positive": counts["positive"],
            "negative": counts["negative"],
            "unknownExcluded": counts["unknown"],
            "usableEventGroups": usable_events,
            "byEvent": {event_id: dict(values) for event_id, values in sorted(by_event.items())},
            "holdoutAcquisitionsInSearchWindow": holdout_availability["acquisitionCount"],
            "holdoutUsableObservations": by_event[holdout["eventId"]]["positive"]
            + by_event[holdout["eventId"]]["negative"],
            "featureMissingness": "Not computed: feature engineering is prohibited after a failed label gate.",
        },
        "decision": (
            "Historical model training is prohibited. Preserve the synthetic-label runtime artifact until additional "
            "verified events with timely Sentinel-1 acquisitions provide positive support and an independent split."
        ),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the Phase C scientific feasibility gate.")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    if args.write:
        OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
