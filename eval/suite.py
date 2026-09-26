from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from eval.adapter import canonical_decision_hash, load_dataset, run_system
from eval.simulator import simulate

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = Path(__file__).with_name("testcases.json")
RESULTS = Path(__file__).with_name("results")
WIB = ZoneInfo("Asia/Jakarta")


def _case_result(
    case: dict[str, Any], defaults: dict[str, Any], frame
) -> dict[str, Any]:
    output = run_system(case, defaults, frame)
    simulation = simulate(output)
    expected = set(case["expectedPlanOutcomes"])
    passed = (
        output["planOutcome"] in expected
        and simulation["metrics"]["constraintViolationRatePercent"] == 0
    )
    return {
        "caseId": case["id"],
        "category": case["category"],
        "passed": passed,
        "expectation": {
            "planOutcomeIn": sorted(expected),
            "constraintViolationRatePercent": 0,
        },
        "decision": {
            "optimizerStatus": output["optimizerStatus"],
            "planOutcome": output["planOutcome"],
            "solverStatusDetail": output["solverStatusDetail"],
            "recommendationCount": len(output["decisions"]),
            "totalEstimatedCostIdr": output["totalEstimatedCostIdr"],
            "limitations": output["limitations"],
            "canonicalDecisionSha256": canonical_decision_hash(output),
        },
        **simulation,
    }


def run_suite(
    cases_path: Path = DEFAULT_CASES, label: str = "baseline"
) -> tuple[Path, dict[str, Any]]:
    specification = json.loads(cases_path.read_text(encoding="utf-8"))
    frame = load_dataset(specification["dataset"])
    cases = [
        _case_result(case, specification["defaults"], frame)
        for case in specification["cases"]
    ]
    total_demand = sum(
        sum(day["demandedCups"] for day in case["daily"]) for case in cases
    )
    total_fulfilled = sum(
        sum(day["fulfilledCups"] for day in case["daily"]) for case in cases
    )
    total_checks = sum(case["metrics"]["constraintChecks"] for case in cases)
    total_violations = sum(
        len(case["metrics"]["constraintViolations"]) for case in cases
    )
    purchase_cost = sum(
        case["metrics"]["costBreakdownIdr"]["purchase"] for case in cases
    )
    holding_cost = sum(case["metrics"]["costBreakdownIdr"]["holding"] for case in cases)
    stockout_cost = sum(
        case["metrics"]["costBreakdownIdr"]["stockout"] for case in cases
    )
    waste_cost = sum(case["metrics"]["costBreakdownIdr"]["waste"] for case in cases)
    result = {
        "suite": "ARUNA Inventory Decision Evaluation",
        "suiteVersion": specification["suiteVersion"],
        "label": label,
        "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "dataset": specification["dataset"],
        "caseCount": len(cases),
        "passedCases": sum(case["passed"] for case in cases),
        "aggregate": {
            "actualDemandCups": total_demand,
            "fulfilledDemandCups": total_fulfilled,
            "serviceLevelPercent": round(total_fulfilled / total_demand * 100, 6)
            if total_demand
            else 100.0,
            "unfulfilledDemandCups": total_demand - total_fulfilled,
            "totalOperationalCostIdr": purchase_cost
            + holding_cost
            + stockout_cost
            + waste_cost,
            "costBreakdownIdr": {
                "purchase": purchase_cost,
                "holding": holding_cost,
                "stockout": stockout_cost,
                "waste": waste_cost,
            },
            "constraintViolationRatePercent": round(
                total_violations / total_checks * 100, 6
            )
            if total_checks
            else None,
            "constraintChecks": total_checks,
            "constraintViolations": total_violations,
        },
        "diagnosticsOnly": {
            "forecastMaeCups": round(
                sum(
                    case["forecastDiagnostics"]["maeCups"]
                    * case["forecastDiagnostics"]["observations"]
                    for case in cases
                )
                / sum(case["forecastDiagnostics"]["observations"] for case in cases),
                6,
            ),
            "forecastRmseCups": round(
                (
                    sum(
                        case["forecastDiagnostics"]["rmseCups"] ** 2
                        * case["forecastDiagnostics"]["observations"]
                        for case in cases
                    )
                    / sum(case["forecastDiagnostics"]["observations"] for case in cases)
                )
                ** 0.5,
                6,
            ),
            "note": "Forecast error is diagnostic and is not an operational success metric.",
        },
        "cases": cases,
        "limitations": [
            "Fixed synthetic demand is ground truth only inside this deterministic evaluation.",
            "No shelf-life or lot-age source exists, so waste is not evaluated.",
            "No validated holding-cost rate exists, so holding cost is reported as zero and unevaluated.",
            "The adapter invokes production forecast and procurement engines but excludes persistence, approval, and Qwen explanation.",
        ],
    }
    RESULTS.mkdir(exist_ok=True)
    timestamp = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")
    path = RESULTS / f"inventory_{label}_{timestamp}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return path, result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the deterministic ARUNA inventory decision evaluation suite."
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--label", default="baseline")
    args = parser.parse_args()
    path, result = run_suite(args.cases, args.label)
    print(f"result={path}")
    print(
        json.dumps(
            {"passedCases": result["passedCases"], **result["aggregate"]}, indent=2
        )
    )


if __name__ == "__main__":
    main()
