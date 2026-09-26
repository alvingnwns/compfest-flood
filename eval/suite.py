from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from eval.adapter import canonical_decision_hash, load_dataset, run_system
from eval.oracle import oracle_diagnostics
from eval.simulator import simulate

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = Path(__file__).with_name("testcases.json")
RESULTS = Path(__file__).with_name("results")
WIB = ZoneInfo("Asia/Jakarta")


def _single_case_result(
    case: dict[str, Any], defaults: dict[str, Any], frame
) -> dict[str, Any]:
    output = run_system(case, defaults, frame)
    simulation = simulate(output)
    # The hindsight oracle runs only after the system decision is fixed.
    oracle = oracle_diagnostics(output, simulation["metrics"])
    expected = set(case["expectedPlanOutcomes"])
    constraint_expectation = case.get("constraintEvaluation", "REQUIRED")
    actual_cvr = simulation["metrics"]["constraintViolationRatePercent"]
    constraint_passed = (
        actual_cvr == 0 if constraint_expectation == "REQUIRED" else actual_cvr is None
    )
    passed = output["planOutcome"] in expected and constraint_passed
    return {
        "caseId": case["id"],
        "category": case["category"],
        "passed": passed,
        "expectation": {
            "planOutcomeIn": sorted(expected),
            "constraintEvaluation": constraint_expectation,
            "constraintViolationRatePercent": 0
            if constraint_expectation == "REQUIRED"
            else None,
        },
        "decision": {
            "optimizerStatus": output["optimizerStatus"],
            "planOutcome": output["planOutcome"],
            "solverStatusDetail": output["solverStatusDetail"],
            "recommendationCount": len(output["decisions"]),
            "totalEstimatedCostIdr": output["totalEstimatedCostIdr"],
            "limitations": output["limitations"],
            "optimizerVersion": output["optimizerVersion"],
            "objectiveStages": output["objectiveStages"],
            "canonicalDecisionSha256": canonical_decision_hash(output),
        },
        **simulation,
        "oracle": oracle,
    }


def _case_result(
    case: dict[str, Any], defaults: dict[str, Any], frame
) -> dict[str, Any]:
    variants = case.get("variants")
    if not variants:
        return _single_case_result(case, defaults, frame)
    runs = []
    primary = None
    for variant in variants:
        merged = {key: value for key, value in case.items() if key != "variants"}
        merged.update(
            {
                key: value
                for key, value in variant.items()
                if key not in {"id", "primary"}
            }
        )
        result = _single_case_result(merged, defaults, frame)
        runs.append({"variantId": variant["id"], **result})
        if variant.get("primary"):
            primary = result
    if primary is None:
        raise ValueError(
            f"Case {case['id']} with variants requires exactly one primary run"
        )
    control = runs[0]
    stress = next(run for run in runs if run["variantId"] != control["variantId"])
    primary["runs"] = runs
    primary["sensitivity"] = {
        "controlVariant": control["variantId"],
        "stressVariant": stress["variantId"],
        "serviceLevelPercentagePoints": round(
            stress["metrics"]["serviceLevelPercent"]
            - control["metrics"]["serviceLevelPercent"],
            6,
        ),
        "unfulfilledDemandCups": (
            stress["metrics"]["unfulfilledDemandCups"]
            - control["metrics"]["unfulfilledDemandCups"]
        ),
        "totalOperationalCostIdr": (
            stress["metrics"]["totalOperationalCostIdr"]
            - control["metrics"]["totalOperationalCostIdr"]
        ),
    }
    primary["passed"] = all(run["passed"] for run in runs)
    return primary


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
    oracle_fulfilled = sum(case["oracle"]["oracleMaximumFulfilledCups"] for case in cases)
    total_cost = purchase_cost + holding_cost + stockout_cost + waste_cost
    oracle_min_cost = sum(case["oracle"]["oracleMinimumCostIdr"] for case in cases)
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
            "totalOperationalCostIdr": total_cost,
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
        "oracleDiagnostics": {
            "oracleMaximumFulfilledCups": oracle_fulfilled,
            "feasibleFulfillmentPercent": round(total_fulfilled / oracle_fulfilled * 100, 6)
            if oracle_fulfilled
            else None,
            "serviceRegretCups": oracle_fulfilled - total_fulfilled,
            "oracleMinimumCostIdr": oracle_min_cost,
            "operationalCostRegretIdr": total_cost - oracle_min_cost,
            "note": "Hindsight bounds use actual demand after decisions are fixed; they are not decision inputs.",
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
