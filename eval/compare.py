"""Same-track comparison between two frozen inventory suite artifacts.

Unlike the legacy bridge, both artifacts come from the same cases, actual demand, simulator and
metric formulas, so deltas here are like-for-like. The hindsight oracle depends only on case inputs,
so the newer artifact's oracle bounds also score the older artifact's decisions.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

RESULTS = Path(__file__).with_name("results")
DEFAULT_ITER1 = RESULTS / "inventory_iter1_20260926_144839.json"
DEFAULT_CASES = Path(__file__).with_name("testcases.json")
WIB = ZoneInfo("Asia/Jakarta")


def _runs(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    runs = {}
    for case in artifact["cases"]:
        for run in case.get("runs", [case]):
            runs[f"{case['caseId']}/{run.get('variantId') or 'primary'}"] = run
    return runs


def _primary_ids(cases_path: Path) -> list[str]:
    """Primary run per case as declared by the frozen testcase specification."""
    ids = []
    for case in json.loads(cases_path.read_text(encoding="utf-8"))["cases"]:
        variant = next((item["id"] for item in case.get("variants", []) if item.get("primary")), None)
        ids.append(f"{case['id']}/{variant or 'primary'}")
    return ids


def _kpi(run: dict[str, Any], oracle: dict[str, Any]) -> dict[str, Any]:
    metrics = run["metrics"]
    fulfilled = metrics["fulfilledDemandCups"]
    oracle_max = oracle["oracleMaximumFulfilledCups"]
    return {
        "planOutcome": run["decision"]["planOutcome"],
        "fulfilledDemandCups": fulfilled,
        "serviceLevelPercent": metrics["serviceLevelPercent"],
        "unfulfilledDemandCups": metrics["unfulfilledDemandCups"],
        "totalOperationalCostIdr": metrics["totalOperationalCostIdr"],
        "purchaseCostIdr": metrics["costBreakdownIdr"]["purchase"],
        "constraintViolations": len(metrics["constraintViolations"]),
        "constraintChecks": metrics["constraintChecks"],
        "feasibleFulfillmentPercent": round(fulfilled / oracle_max * 100, 6) if oracle_max else None,
        "serviceRegretCups": oracle_max - fulfilled,
        "operationalCostRegretIdr": metrics["totalOperationalCostIdr"] - oracle["oracleMinimumCostIdr"],
    }


def _delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "fulfilledDemandCups",
        "serviceLevelPercent",
        "unfulfilledDemandCups",
        "totalOperationalCostIdr",
        "purchaseCostIdr",
        "serviceRegretCups",
        "operationalCostRegretIdr",
    ]
    delta = {key: round(after[key] - before[key], 6) for key in keys}
    if before["feasibleFulfillmentPercent"] is not None and after["feasibleFulfillmentPercent"] is not None:
        delta["feasibleFulfillmentPercentagePoints"] = round(
            after["feasibleFulfillmentPercent"] - before["feasibleFulfillmentPercent"], 6
        )
    return delta


def compare(before_path: Path, after_path: Path, cases_path: Path = DEFAULT_CASES) -> dict[str, Any]:
    before = json.loads(before_path.read_text(encoding="utf-8"))
    after = json.loads(after_path.read_text(encoding="utf-8"))
    specification = json.loads(cases_path.read_text(encoding="utf-8"))
    for key in ("suite", "suiteVersion", "dataset"):
        if before[key] != after[key]:
            raise ValueError(f"Artifacts differ in {key}; comparison would not be like-for-like")
    if after["suiteVersion"] != specification["suiteVersion"] or after["dataset"] != specification["dataset"]:
        raise ValueError("Artifacts were not produced from the current frozen testcase specification")
    before_runs, after_runs = _runs(before), _runs(after)
    if before_runs.keys() != after_runs.keys():
        raise ValueError("Artifacts contain different case runs")
    for run_id, run in after_runs.items():
        if "oracle" not in run:
            raise ValueError(f"{run_id} lacks oracle diagnostics; rerun the newer suite")
        if [day["demandedCups"] for day in run["daily"]] != [day["demandedCups"] for day in before_runs[run_id]["daily"]]:
            raise ValueError(f"{run_id} actual demand differs between artifacts")

    runs = []
    for run_id, after_run in after_runs.items():
        oracle = after_run["oracle"]
        old = _kpi(before_runs[run_id], oracle)
        new = _kpi(after_run, oracle)
        runs.append(
            {
                "runId": run_id,
                "actualDemandCups": after_run["metrics"]["actualDemandCups"],
                "oracleMaximumFulfilledCups": oracle["oracleMaximumFulfilledCups"],
                "oracleMinimumCostIdr": oracle["oracleMinimumCostIdr"],
                "before": old,
                "after": new,
                "delta": _delta(old, new),
                "decisionChanged": before_runs[run_id]["decision"]["canonicalDecisionSha256"]
                != after_run["decision"]["canonicalDecisionSha256"],
            }
        )

    primary = _primary_ids(cases_path)
    if not set(primary) <= after_runs.keys():
        raise ValueError("Testcase specification and artifacts disagree on case runs")
    by_id = {run["runId"]: run for run in runs}

    def aggregate(side: str) -> dict[str, Any]:
        demand = sum(by_id[run_id]["actualDemandCups"] for run_id in primary)
        fulfilled = sum(by_id[run_id][side]["fulfilledDemandCups"] for run_id in primary)
        oracle_max = sum(by_id[run_id]["oracleMaximumFulfilledCups"] for run_id in primary)
        cost = sum(by_id[run_id][side]["totalOperationalCostIdr"] for run_id in primary)
        oracle_cost = sum(by_id[run_id]["oracleMinimumCostIdr"] for run_id in primary)
        return {
            "actualDemandCups": demand,
            "fulfilledDemandCups": fulfilled,
            "serviceLevelPercent": round(fulfilled / demand * 100, 6),
            "unfulfilledDemandCups": demand - fulfilled,
            "totalOperationalCostIdr": cost,
            "constraintViolations": sum(by_id[run_id][side]["constraintViolations"] for run_id in primary),
            "constraintChecks": sum(by_id[run_id][side]["constraintChecks"] for run_id in primary),
            "feasibleFulfillmentPercent": round(fulfilled / oracle_max * 100, 6),
            "serviceRegretCups": oracle_max - fulfilled,
            "operationalCostRegretIdr": cost - oracle_cost,
        }

    old_total, new_total = aggregate("before"), aggregate("after")
    return {
        "comparison": "inventory same-track iteration comparison",
        "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "beforeArtifact": before_path.as_posix(),
        "afterArtifact": after_path.as_posix(),
        "suiteVersion": after["suiteVersion"],
        "dataset": after["dataset"],
        "primaryRuns": primary,
        "aggregate": {
            "before": old_total,
            "after": new_total,
            "delta": {
                key: round(new_total[key] - old_total[key], 6)
                for key in old_total
                if key not in {"actualDemandCups", "constraintChecks"}
            },
        },
        "runs": runs,
        "guards": [
            "Identical suite, suiteVersion, dataset hash, case runs and daily actual demand are asserted.",
            "Oracle bounds come from case inputs and actual demand only and never feed decisions.",
            "Holding and waste remain unevaluated in both artifacts.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two inventory suite artifacts like-for-like.")
    parser.add_argument("--before", type=Path, default=DEFAULT_ITER1)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.before, args.after)
    RESULTS.mkdir(exist_ok=True)
    timestamp = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")
    output = RESULTS / f"compare_inventory_iter1_iter2_{timestamp}.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"result={output}")
    print(json.dumps(result["aggregate"], indent=2))


if __name__ == "__main__":
    main()
