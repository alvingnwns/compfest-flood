from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from eval.workbook import load_nominal

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).with_name("results")
DEFAULT_LEGACY = RESULTS / "baseline_20260926_111142.json"
WIB = ZoneInfo("Asia/Jakarta")


def _demand_value(data: dict[str, list[dict[str, Any]]]) -> int:
    prices = {row["productId"]: int(row["sellingPrice"]) for row in data["Products"]}
    return sum(
        int(row["quantity"]) * prices[row["productId"]] for row in data["Orders"]
    )


def _metric_view(
    *,
    actual: int,
    fulfilled: int,
    total_cost: int,
    cost_breakdown: dict[str, int | None],
    violations: int,
    checks: int,
    demand_value: int,
) -> dict[str, Any]:
    unfulfilled = actual - fulfilled
    return {
        "actualDemandUnits": actual,
        "fulfilledDemandUnits": fulfilled,
        "serviceLevelPercent": round(fulfilled / actual * 100, 6) if actual else 100.0,
        "unfulfilledDemandUnits": unfulfilled,
        "unfulfilledDemandRatePercent": round(unfulfilled / actual * 100, 6)
        if actual
        else 0.0,
        "totalOperationalCostIdr": total_cost,
        "operationalCostPerDemandUnitIdr": round(total_cost / actual, 2)
        if actual
        else None,
        "operationalCostToDemandValuePercent": round(total_cost / demand_value * 100, 6)
        if demand_value
        else None,
        "costBreakdownIdr": cost_breakdown,
        "constraintViolationRatePercent": round(violations / checks * 100, 6)
        if checks
        else None,
        "constraintChecks": checks,
        "constraintViolations": violations,
    }


def _legacy_metrics(
    case: dict[str, Any], rainfall: str | None, demand_value: int
) -> dict[str, Any]:
    run = next(
        item
        for item in case["runs"]
        if rainfall is None or item["rainfall_scenario"] == rainfall
    )
    outcome = run["outcome_metrics"]["recovery"]
    checks = int(outcome["constraint_checks"])
    violations = int(run["constraint_checks"]["recovery"]["violations"])
    actual = int(outcome["requested_units"])
    fulfilled = actual - int(outcome["unfulfilled_demand_units"])
    loss = round(outcome["operational_loss_idr"])
    return {
        "sourceCaseId": case["case_id"],
        "sourceVariant": rainfall,
        "decisionStatus": run["actual_status"],
        "metrics": _metric_view(
            actual=actual,
            fulfilled=fulfilled,
            total_cost=loss,
            cost_breakdown={
                "purchase": None,
                "holding": None,
                "stockout": loss,
                "waste": None,
            },
            violations=violations,
            checks=checks,
            demand_value=demand_value,
        ),
        "coverage": {
            "purchase": "NOT_MODELED",
            "holding": "NOT_MODELED",
            "stockout": "SALES_EXPOSURE_RISK_PROXY",
            "waste": "NOT_MODELED",
        },
    }


def _inventory_metrics(
    case: dict[str, Any], selling_price: int, variant: str | None = None
) -> dict[str, Any]:
    selected = case
    if variant is not None:
        selected = next(run for run in case["runs"] if run["variantId"] == variant)
    metrics = selected["metrics"]
    actual = int(metrics["actualDemandCups"])
    fulfilled = int(metrics["fulfilledDemandCups"])
    breakdown = {key: int(value) for key, value in metrics["costBreakdownIdr"].items()}
    return {
        "sourceCaseId": case["caseId"],
        "sourceVariant": variant,
        "decisionStatus": selected["decision"]["planOutcome"],
        "metrics": _metric_view(
            actual=actual,
            fulfilled=fulfilled,
            total_cost=int(metrics["totalOperationalCostIdr"]),
            cost_breakdown=breakdown,
            violations=len(metrics["constraintViolations"]),
            checks=int(metrics["constraintChecks"]),
            demand_value=actual * selling_price,
        ),
        "coverage": {
            "purchase": "EVALUATED",
            "holding": "NOT_EVALUATED_NO_RATE",
            "stockout": "UNFULFILLED_CUPS_X_FIXED_SELLING_PRICE",
            "waste": "NOT_EVALUATED_NO_SHELF_LIFE",
        },
    }


def build_bridge(legacy_path: Path, inventory_path: Path) -> dict[str, Any]:
    legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    legacy_cases = {case["case_id"]: case for case in legacy["cases"]}
    inventory_cases = {case["caseId"]: case for case in inventory["cases"]}
    nominal, _ = load_nominal()
    nominal_value = _demand_value(nominal)
    impossible = json.loads(json.dumps(nominal))
    next(row for row in impossible["Orders"] if row["orderId"] == "ORDER-001")[
        "quantity"
    ] *= 10
    impossible_value = _demand_value(impossible)
    pairs = [
        (
            "B01-normal",
            "Nominal operating condition",
            _legacy_metrics(legacy_cases["C1"], None, nominal_value),
            _inventory_metrics(inventory_cases["I01-normal-demand"], 20_000),
        ),
        (
            "B02-impossible",
            "Impossible input or procurement condition",
            _legacy_metrics(legacy_cases["C2"], None, impossible_value),
            _inventory_metrics(inventory_cases["I02-procurement-impossible"], 20_000),
        ),
        (
            "B03-heavy-pressure",
            "Heavy hazard or operational constraint pressure",
            _legacy_metrics(legacy_cases["C5"], "Q4", nominal_value),
            _inventory_metrics(
                inventory_cases["I03-heavy-constraint-pressure"], 20_000, "heavy"
            ),
        ),
    ]
    comparisons = []
    for pair_id, archetype, old, new in pairs:
        old_metrics = old["metrics"]
        new_metrics = new["metrics"]
        comparisons.append(
            {
                "pairId": pair_id,
                "archetype": archetype,
                "legacyRecovery": old,
                "inventoryIteration1": new,
                "contextualDelta": {
                    "serviceLevelPercentagePoints": round(
                        new_metrics["serviceLevelPercent"]
                        - old_metrics["serviceLevelPercent"],
                        6,
                    ),
                    "unfulfilledDemandRatePercentagePoints": round(
                        new_metrics["unfulfilledDemandRatePercent"]
                        - old_metrics["unfulfilledDemandRatePercent"],
                        6,
                    ),
                    "operationalCostToDemandValuePercentagePoints": round(
                        new_metrics["operationalCostToDemandValuePercent"]
                        - old_metrics["operationalCostToDemandValuePercent"],
                        6,
                    ),
                    "causalImprovementClaimAllowed": False,
                },
            }
        )
    legacy_control = _legacy_metrics(legacy_cases["C5"], "Q1", nominal_value)
    legacy_stress = _legacy_metrics(legacy_cases["C5"], "Q4", nominal_value)
    inventory_control = _inventory_metrics(
        inventory_cases["I03-heavy-constraint-pressure"], 20_000, "control"
    )
    inventory_stress = _inventory_metrics(
        inventory_cases["I03-heavy-constraint-pressure"], 20_000, "heavy"
    )

    def sensitivity_delta(
        control: dict[str, Any], stress: dict[str, Any]
    ) -> dict[str, Any]:
        before = control["metrics"]
        after = stress["metrics"]
        return {
            "serviceLevelPercentagePoints": round(
                after["serviceLevelPercent"] - before["serviceLevelPercent"], 6
            ),
            "unfulfilledDemandUnits": (
                after["unfulfilledDemandUnits"] - before["unfulfilledDemandUnits"]
            ),
            "totalOperationalCostIdr": (
                after["totalOperationalCostIdr"] - before["totalOperationalCostIdr"]
            ),
        }

    return {
        "bridgeVersion": "legacy-inventory-context-v2",
        "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "experiment": {
            "baseline": "legacy ARUNA recovery without XGBoost forecast or Qwen reasoning",
            "iteration1": "new ARUNA inventory risk, XGBoost forecast, and procurement optimization",
            "legacyOptimizer": "deterministic CP-SAT/OR-Tools",
            "comparisonType": "formula-aligned contextual bridge",
        },
        "legacyArtifact": legacy_path.as_posix(),
        "inventoryArtifact": inventory_path.as_posix(),
        "formula": {
            "serviceLevel": "fulfilled demand units / actual demand units * 100%",
            "unfulfilledDemand": "actual demand units - fulfilled demand units",
            "totalOperationalCost": "purchase + holding + stockout + waste",
            "constraintViolationRate": "violated constraints / evaluated constraints * 100%",
        },
        "comparisons": comparisons,
        "matchedSensitivity": {
            "design": "fixed ground truth within each track; control then stress",
            "legacy": {
                "control": legacy_control,
                "stress": legacy_stress,
                "delta": sensitivity_delta(legacy_control, legacy_stress),
            },
            "inventory": {
                "control": inventory_control,
                "stress": inventory_stress,
                "delta": sensitivity_delta(inventory_control, inventory_stress),
            },
            "crossTrackDeltaComparisonIsCausal": False,
        },
        "interpretation": [
            "Scenario archetypes and formulas are aligned, but source domains and demand units differ.",
            "Absolute demand and IDR totals must not be subtracted across tracks.",
            "Contextual deltas are descriptive normalized rates, not causal product improvement.",
            "Legacy operational cost contains only the sales-exposure stockout proxy.",
            "Inventory holding and waste costs remain unevaluated because their source data is absent.",
            "CVR is null when no decision exists and zero constraints can be evaluated.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a guarded legacy-to-inventory metric bridge."
    )
    parser.add_argument("--legacy", type=Path, default=DEFAULT_LEGACY)
    parser.add_argument("--inventory", type=Path, required=True)
    args = parser.parse_args()
    result = build_bridge(args.legacy, args.inventory)
    RESULTS.mkdir(exist_ok=True)
    timestamp = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")
    output = RESULTS / f"bridge_legacy_inventory_{timestamp}.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"result={output}")


if __name__ == "__main__":
    main()
