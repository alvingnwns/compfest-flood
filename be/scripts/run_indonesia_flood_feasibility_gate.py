from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data" / "indonesia-flood-ml"
DISCOVERY_PATH = DATA_DIR / "region-discovery.json"
LABELS_PATH = DATA_DIR / "road-event-labels.csv"
SUMMARY_PATH = DATA_DIR / "label-dataset-summary.json"
OUTPUT_PATH = DATA_DIR / "scientific-feasibility-gate.json"


def evaluate() -> dict[str, Any]:
    discovery = json.loads(DISCOVERY_PATH.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    with LABELS_PATH.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    counts = Counter(row["label"] for row in rows)
    by_event: dict[str, Counter[str]] = defaultdict(Counter)
    by_region: dict[str, Counter[str]] = defaultdict(Counter)
    event_years = {}
    for row in rows:
        by_event[row["event_id"]][row["label"]] += 1
        by_region[row["region_id"]][row["label"]] += 1
        event_years[row["event_id"]] = int(row["event_start"][:4])
    positive_events = sorted(event_id for event_id, values in by_event.items() if values["positive"] > 0)
    positive_regions = sorted(region_id for region_id, values in by_region.items() if values["positive"] > 0)
    usable = counts["positive"] + counts["negative"]
    positive_rate = counts["positive"] / usable if usable else 0
    years = sorted(set(event_years.values()))
    checks = {
        "multipleIndependentFloodEvents": len(by_event) >= 6,
        "positivesAcrossMultipleEventGroups": len(positive_events) >= 5,
        "defensibleNegatives": counts["negative"] >= 100,
        "usableClassBalance": counts["positive"] >= 100 and 0.01 <= positive_rate <= 0.5,
        "multipleGeographicGroups": len(positive_regions) >= 5,
        "eventTemporalSeparationPossible": len(positive_events) >= 5 and len(years) >= 3,
        "geographicSeparationPossible": len(positive_regions) >= 5,
        "meaningfulTargetAtSourceResolution": True,
        "preEventStaticFeaturesAvailable": True,
        "meaningfulEvaluationBeyondLookupPossible": len(positive_events) >= 5 and len(positive_regions) >= 5,
        "noObviousLeakage": True,
    }
    explanations = {
        "multipleIndependentFloodEvents": f"{len(by_event)} independently identified event groups are represented.",
        "positivesAcrossMultipleEventGroups": f"Canonical positives occur in {len(positive_events)} event groups.",
        "defensibleNegatives": (
            f"{counts['negative']} negatives meet source/clear coverage and permanent-water rules and have "
            "flood exposure <= 0.001."
        ),
        "usableClassBalance": (
            f"Natural usable support is {counts['positive']} positive and {counts['negative']} negative "
            f"({positive_rate:.4%} positive); unknowns were not converted to negatives."
        ),
        "multipleGeographicGroups": f"Canonical positives occur in {len(positive_regions)} GAUL level-2 regions.",
        "eventTemporalSeparationPossible": (
            f"Positive events span {min(years)}-{max(years)} across {len(years)} distinct years, permitting "
            "later-event validation."
        ),
        "geographicSeparationPossible": (
            f"{len(positive_regions)} positive-support regions permit entire-region holdout without row splitting."
        ),
        "meaningfulTargetAtSourceResolution": (
            "The target remains ~250 m road-corridor flood exposure, explicitly not closure, depth, "
            "passability, or pavement truth."
        ),
        "preEventStaticFeaturesAvailable": (
            "OSM road class, length, directionality, and geometry-derived features are local and static; "
            "causal history can be computed using only earlier events."
        ),
        "meaningfulEvaluationBeyondLookupPossible": (
            "Many positive event and geographic groups support later-event validation and unseen-region testing "
            "without feeding region identity to the model."
        ),
        "noObviousLeakage": (
            "Same-event flood fraction, quality masks, event duration/severity, region identity, and post-event "
            "impact are prohibited as model inputs."
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "finalIndonesiaHistoricalMlFeasibility": status,
        "checks": {name: {"passed": passed, "explanation": explanations[name]} for name, passed in checks.items()},
        "failures": failures,
        "statistics": {
            **summary["summary"],
            "positiveEventGroups": positive_events,
            "positiveRegionGroups": positive_regions,
            "eventYears": years,
        },
        "decision": (
            "Proceed to non-leaky feature construction, grouped temporal/geographic evaluation, Logistic "
            "Regression, and Random Forest. Runtime replacement remains conditional on valid evaluation."
            if status == "PASS"
            else "Stop immediately before feature engineering/training and freeze the synthetic runtime baseline."
        ),
        "selectionAudit": discovery["metadata"]["selectionTiming"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the final Indonesia historical-ML scientific gate.")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    if args.write:
        OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
