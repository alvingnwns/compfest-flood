from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
DISCOVERY_PATH = DATA_DIR / "global-flood-db" / "event-discovery.json"
LABELS_PATH = DATA_DIR / "datasets" / "global_flood_road_corridor_labels.csv"
SENSITIVITY_PATH = DATA_DIR / "global-flood-db" / "corridor-sensitivity.json"
SENTINEL_GATE_PATH = DATA_DIR / "flood-events" / "scientific-feasibility-gate.json"
RUNTIME_METRICS_PATH = BASE_DIR / "app" / "models" / "flood_risk_metrics.json"
OUTPUT_PATH = DATA_DIR / "global-flood-db" / "scientific-feasibility-gate.json"


def evaluate() -> dict[str, Any]:
    discovery = json.loads(DISCOVERY_PATH.read_text(encoding="utf-8"))
    sensitivity = json.loads(SENSITIVITY_PATH.read_text(encoding="utf-8"))
    sentinel_gate = json.loads(SENTINEL_GATE_PATH.read_text(encoding="utf-8"))
    runtime_metrics = json.loads(RUNTIME_METRICS_PATH.read_text(encoding="utf-8"))
    with LABELS_PATH.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    counts = Counter(row["label"] for row in rows)
    by_event: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        by_event[row["event_id"]][row["label"]] += 1
    detected_events = [
        event for event in discovery["events"] if event["intersectionStatus"] == "detected_non_permanent_flood"
    ]
    context_eligible_events = {row["event_id"] for row in rows if row["event_context_confidence"] != "low"}
    positive_event_groups = {event_id for event_id, values in by_event.items() if values["positive"] > 0}
    usable = counts["positive"] + counts["negative"]
    positive_rate = counts["positive"] / usable if usable else 0
    stable_positive_configurations = sum(
        configuration["positive"] > 0 for configuration in sensitivity["configurations"]
    )
    checks = {
        "multipleIndependentHistoricalEvents": len(context_eligible_events) >= 3,
        "multiplePositiveEventGroups": len(positive_event_groups) >= 3,
        "defensibleNegatives": counts["negative"] >= 30,
        "usableLabelBalance": counts["positive"] >= 30 and 0.01 <= positive_rate <= 0.5,
        "eventTemporalSplitPossible": len(positive_event_groups) >= 3,
        "meaningfulTargetAtSourceResolution": True,
        "sufficientPreEventStaticFeaturesAvailable": True,
        "noObviousTargetLeakage": True,
        "evaluationTestsBetweenEventGeneralization": len(positive_event_groups) >= 3,
    }
    explanations = {
        "multipleIndependentHistoricalEvents": (
            f"Only {len(detected_events)} products contain non-permanent flood pixels in the pilot, and only "
            f"{len(context_eligible_events)} has event context centred on the pilot."
        ),
        "multiplePositiveEventGroups": (
            f"The canonical configuration has positives in {len(positive_event_groups)} independent event groups."
        ),
        "defensibleNegatives": (
            f"{counts['negative']} observations have sufficient clear coverage, low permanent-water overlap, "
            "and zero meaningful flood exposure."
        ),
        "usableLabelBalance": (
            f"Canonical support is {counts['positive']} positive and {counts['negative']} negative; "
            f"positive rate among usable labels is {positive_rate:.6f}."
        ),
        "eventTemporalSplitPossible": (
            "At least three positive-support event groups are required for non-random train/validation/test roles."
        ),
        "meaningfulTargetAtSourceResolution": (
            "The target is explicitly corridor exposure with a one-pixel-radius canonical buffer, not pavement "
            "inundation or road closure."
        ),
        "sufficientPreEventStaticFeaturesAvailable": (
            "OSM road class and length are available before an event; feature construction was intentionally "
            "stopped after this failed label gate."
        ),
        "noObviousTargetLeakage": (
            "No same-event flood, duration, severity, damage, or label-derived value was built as a feature."
        ),
        "evaluationTestsBetweenEventGeneralization": (
            "With no canonical positive event group, independent-event generalization cannot be evaluated."
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "finalRealHistoricalMlFeasibility": "PASS" if all(checks.values()) else "FAIL",
        "checks": {name: {"passed": passed, "explanation": explanations[name]} for name, passed in checks.items()},
        "failures": failures,
        "statistics": {
            "collectionEvents": discovery["metadata"]["collectionEventCount"],
            "productGeometriesIntersectingPilot": discovery["summary"]["productGeometriesIntersectingPilot"],
            "detectedFloodEventsInPilot": len(detected_events),
            "independentlyOfficiallyConfirmedDetectedEvents": discovery["summary"][
                "independentlyOfficiallyConfirmedDetectedEvents"
            ],
            "contextEligibleEvents": sorted(context_eligible_events),
            "positiveEventGroups": sorted(positive_event_groups),
            "roadSegments": len({row["segment_id"] for row in rows}),
            "roadEventObservations": len(rows),
            "positive": counts["positive"],
            "negative": counts["negative"],
            "unknownExcluded": counts["unknown"],
            "positiveRateAmongUsable": round(positive_rate, 6),
            "byEvent": {event_id: dict(values) for event_id, values in sorted(by_event.items())},
            "sensitivityConfigurationsWithAnyPositive": stable_positive_configurations,
            "march2025Role": "demo_only_not_a_global_flood_database_evaluation_event",
        },
        "priorSentinelAttemptStatus": sentinel_gate["status"],
        "activeRuntimeTrainingData": runtime_metrics["trainingData"],
        "decision": (
            "Stop before feature engineering and training. Keep the transparent synthetic ML baseline for the "
            "competition MVP; do not replace the active runtime artifact."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the final Global Flood Database feasibility gate.")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    if args.write:
        OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
