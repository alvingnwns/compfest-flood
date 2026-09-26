"""ARUNA Phase I baseline evaluation. Run from the repo root: python -m eval.run_eval"""

from __future__ import annotations

import copy
import json
import sys
import traceback
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "be"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402

from app.business_import.repository import business_snapshot_repository  # noqa: E402
from app.main import app  # noqa: E402
from app.repositories.simulation_repository import simulation_repository  # noqa: E402
from eval.checker import CheckReport, Network, check_plan  # noqa: E402
from eval.workbook import XLSX_MIME, BusinessData, build_workbook, load_nominal  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent / "results"
FEASIBLE_STATUSES = {"ready", "partial"}
KPI_KEYS = ("orders-fulfilled", "on-time-delivery", "failed-orders", "average-delay", "sales-exposure-risk")
PENDING_CASES = ("C3", "C4", "C6")


class HttpFailure(Exception):
    def __init__(self, step: str, status_code: int, body: Any) -> None:
        super().__init__(f"{step} -> HTTP {status_code}")
        self.step = step
        self.status_code = status_code
        self.body = body


def _call(client: TestClient, method: str, url: str, step: str, expected: int, **kwargs: Any) -> Any:
    response = client.request(method, url, **kwargs)
    try:
        body = response.json()
    except ValueError:
        body = response.text
    if response.status_code != expected:
        raise HttpFailure(step, response.status_code, body)
    return body


class Context:
    def __init__(self, client: TestClient, nominal: BusinessData, data_source: str) -> None:
        self.client = client
        self.nominal = nominal
        self.data_source = data_source
        scenario = _call(client, "GET", "/api/scenarios/historical-jakarta", "get-scenario", 200)
        self.scenario_id: str = scenario["id"]
        self.base_vehicles = {
            vehicle["id"]: {"capacity": vehicle["capacityUnits"], "available": vehicle["available"]}
            for vehicle in scenario["vehicles"]
        }
        self.factory_capacity = sum(
            facility.get("productionCapacityUnits") or 0
            for facility in scenario["facilities"]
            if facility["kind"] == "factory"
        )
        # Mirrors the documented import rule: each store keeps its most common demo warehouse.
        by_store: dict[str, list[str]] = {}
        for order in scenario["orders"]:
            by_store.setdefault(order["storeId"], []).append(order["preferredWarehouseId"])
        self.preferred_warehouse = {
            store: Counter(choices).most_common(1)[0][0] for store, choices in by_store.items()
        }

    def vehicles_with(self, overrides: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        vehicles = copy.deepcopy(self.base_vehicles)
        for override in overrides:
            target = vehicles.get(override["id"])
            if target is None:
                continue
            if override.get("capacityUnits") is not None:
                target["capacity"] = override["capacityUnits"]
            if override.get("available") is not None:
                target["available"] = override["available"]
        return vehicles


def _kpis(impact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metrics = {metric["key"]: metric for metric in impact["metrics"]}
    return {
        key: {"baseline": metrics[key]["baseline"], "recovery": metrics[key]["recovery"]}
        for key in KPI_KEYS
        if key in metrics
    }


def _outcome_metrics(
    data: BusinessData,
    kpis: dict[str, dict[str, Any]],
    plan_outcomes: dict[str, list[dict[str, Any]]],
    reports: dict[str, CheckReport],
) -> dict[str, dict[str, Any]]:
    total_orders = len(data["Orders"])
    requested_units = sum(int(row["quantity"]) for row in data["Orders"])
    metrics = {}
    for plan in ("baseline", "recovery"):
        allocated_units = sum(int(outcome["allocated_quantity"]) for outcome in plan_outcomes[plan])
        report = reports[plan]
        metrics[plan] = {
            "service_level": round(kpis["orders-fulfilled"][plan] / total_orders, 4) if total_orders else 0.0,
            "unfulfilled_demand_units": requested_units - allocated_units,
            "requested_units": requested_units,
            "operational_loss_idr": kpis["sales-exposure-risk"][plan],
            "constraint_violation_rate": round(len(report.violations) / report.checks, 4) if report.checks else None,
            "constraint_checks": report.checks,
        }
    return metrics


def run_pipeline(
    ctx: Context,
    *,
    data: BusinessData,
    rainfall: str,
    vehicle_overrides: list[dict[str, Any]] | None = None,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """import -> simulation -> disruption -> recovery -> impact, then independent constraint checks."""
    vehicle_overrides = vehicle_overrides or []
    constraints = constraints or {"allowSubstitution": False}
    run: dict[str, Any] = {
        "rainfall_scenario": rainfall,
        "vehicle_overrides": vehicle_overrides,
        "recovery_constraints": constraints,
    }
    client = ctx.client
    try:
        imported = _call(
            client,
            "POST",
            "/api/business-data/import",
            "business-import",
            201,
            files={"file": ("eval_case.xlsx", build_workbook(data), XLSX_MIME)},
        )
        simulation = _call(
            client,
            "POST",
            "/api/simulations",
            "run-simulation",
            201,
            json={
                "scenarioId": ctx.scenario_id,
                "analysisMode": "scenario-simulation",
                "region": "jakarta",
                "rainfallScenario": rainfall,
                "businessSnapshotId": imported["businessSnapshotId"],
                "vehicleOverrides": vehicle_overrides,
            },
        )
        simulation_id = simulation["id"]
        disruption = _call(client, "GET", f"/api/simulations/{simulation_id}/disruption", "get-disruption", 200)
        _call(
            client,
            "POST",
            f"/api/simulations/{simulation_id}/recovery",
            "create-recovery",
            201,
            json={"constraints": constraints},
        )
        recovery = _call(client, "GET", f"/api/simulations/{simulation_id}/recovery", "get-recovery", 200)
        impact = _call(client, "GET", f"/api/simulations/{simulation_id}/impact", "get-impact", 200)
    except HttpFailure as failure:
        run.update(
            actual_status=f"http-{failure.status_code}",
            http_failure={"step": failure.step, "status_code": failure.status_code, "body": failure.body},
        )
        return run

    # Per-order outcomes and production are excluded from the HTTP schema; read them in-process.
    stored = simulation_repository.get_recovery(simulation_id)
    plan_outcomes = {
        "baseline": [outcome.model_dump(mode="json") for outcome in stored.baseline_order_outcomes],
        "recovery": [outcome.model_dump(mode="json") for outcome in stored.recovery_order_outcomes],
    }
    plan_production = {
        "baseline": {item.product_id: item.quantity for item in stored.baseline_production},
        "recovery": {item.product_id: item.quantity for item in stored.recovery_production},
    }
    recovery_allocations = {
        action["orderId"]: [(line["productId"], line["quantity"]) for line in action["allocations"]]
        for action in recovery.get("commerceActions", [])
    }
    routes = {
        route["id"]: {
            "origin": route["originFacilityId"],
            "destination": route["destinationFacilityId"],
            "flood_exposure": route["floodExposure"],
            "type": route["type"],
        }
        for route in disruption["routes"]
    }
    network = Network(
        vehicles=ctx.vehicles_with(vehicle_overrides),
        preferred_warehouse=ctx.preferred_warehouse,
        factory_capacity=ctx.factory_capacity,
        routes=routes,
    )
    reports = {
        "baseline": check_plan(
            plan="baseline",
            data=data,
            network=network,
            outcomes=plan_outcomes["baseline"],
            production=plan_production["baseline"],
            allocations=None,
            allow_substitution=False,
        ),
        "recovery": check_plan(
            plan="recovery",
            data=data,
            network=network,
            outcomes=plan_outcomes["recovery"],
            production=plan_production["recovery"],
            allocations=recovery_allocations,
            allow_substitution=bool(constraints.get("allowSubstitution")),
        ),
    }
    kpis = _kpis(impact)
    orders = {row["orderId"]: row for row in data["Orders"]}
    delivery_routes = [route for route in routes.values() if route["destination"] in ctx.preferred_warehouse]
    run.update(
        simulation_id=simulation_id,
        business_snapshot_id=imported["businessSnapshotId"],
        actual_status=recovery["status"],
        recovery_error=recovery.get("error"),
        hazard=simulation.get("hazard"),
        route_exposure_counts={
            route_type: dict(
                sorted(Counter(r["flood_exposure"] for r in delivery_routes if r["type"] == route_type).items())
            )
            for route_type in ("baseline", "recovery")
        },
        baseline_plan_feasible=bool(plan_outcomes["baseline"]),
        recovery_plan_feasible=bool(plan_outcomes["recovery"]),
        kpis=kpis,
        outcome_metrics=_outcome_metrics(data, kpis, plan_outcomes, reports),
        not_fully_fulfilled={
            plan: [
                {
                    "order_id": outcome["order_id"],
                    "priority": orders[outcome["order_id"]]["priority"],
                    "allocated": outcome["allocated_quantity"],
                    "requested": outcome["requested_quantity"],
                }
                for outcome in plan_outcomes[plan]
                if outcome["allocated_quantity"] < outcome["requested_quantity"]
            ]
            for plan in ("baseline", "recovery")
        },
        constraint_checks={plan: report.as_dict() for plan, report in reports.items()},
        constraint_violations=sum(len(report.violations) for report in reports.values()),
    )
    return run


def _fmt_idr(value: float) -> str:
    return f"IDR {value:,.0f}"


def case_c1(ctx: Context) -> dict[str, Any]:
    run = run_pipeline(ctx, data=copy.deepcopy(ctx.nominal), rainfall="Q2")
    status = run["actual_status"]
    passed = status in FEASIBLE_STATUSES and run.get("constraint_violations") == 0
    findings = []
    if "kpis" in run:
        kpis = run["kpis"]
        total = len(ctx.nominal["Orders"])
        for plan in ("baseline", "recovery"):
            failed = run["not_fully_fulfilled"][plan]
            critical = [item["order_id"] for item in failed if item["priority"] == "critical"]
            findings.append(
                f"{plan}: {int(kpis['orders-fulfilled'][plan])}/{total} order terpenuhi penuh, "
                f"{int(kpis['failed-orders'][plan])} gagal total, {len(failed)} tidak terpenuhi penuh"
                + (f" (termasuk critical: {', '.join(critical)})" if critical else "")
                + f"; sales exposure {_fmt_idr(kpis['sales-exposure-risk'][plan])}."
            )
        if not run["baseline_plan_feasible"]:
            findings.append("Baseline plan infeasible pada data nominal: KPI baseline dihitung dari 0 alokasi.")
    return {
        "case_id": "C1",
        "name": "nominal-baseline",
        "mutation": "Data workbook apa adanya, rainfall Q2.",
        "expectation": "status ready/partial dan 0 constraint violation; catat seluruh KPI baseline vs recovery.",
        "passed": passed,
        "actual_status": status,
        "constraint_violations": run.get("constraint_violations"),
        "findings": findings,
        "runs": [run],
    }


def case_c2(ctx: Context) -> dict[str, Any]:
    data = copy.deepcopy(ctx.nominal)
    target = next(row for row in data["Orders"] if row["orderId"] == "ORDER-001")
    original_quantity = int(target["quantity"])
    target["quantity"] = original_quantity * 10
    run = run_pipeline(ctx, data=data, rainfall="Q2")
    status = run["actual_status"]
    passed = status == "no-feasible-plan"
    findings = []
    if "kpis" in run:
        kpis = run["kpis"]
        total = len(data["Orders"])
        largest_vehicle = max(vehicle["capacity"] for vehicle in ctx.base_vehicles.values())
        findings.append(
            f"ORDER-001 (critical) dinaikkan {original_quantity} -> {target['quantity']} unit, melebihi kendaraan "
            f"terbesar ({largest_vehicle} unit; satu order hanya boleh satu kendaraan)."
        )
        if status == "no-feasible-plan":
            findings.append(
                "All-or-nothing failure: satu order critical yang mustahil membuat seluruh plan recovery "
                f"'no-feasible-plan' -> {int(kpis['orders-fulfilled']['recovery'])}/{total} order terpenuhi, "
                f"{int(kpis['failed-orders']['recovery'])}/{total} gagal total, sales exposure recovery "
                f"{_fmt_idr(kpis['sales-exposure-risk']['recovery'])}. Tidak ada partial plan untuk 19 order lain."
            )
        if not run["baseline_plan_feasible"]:
            findings.append(
                "Baseline plan juga infeasible (constraint critical sama-sama hard): KPI baseline = 0 alokasi, "
                "sehingga perbandingan baseline vs recovery tidak informatif."
            )
        findings.append(
            "Status HTTP recovery tetap 201 dan response tidak menyebut order mana penyebab infeasibility "
            f"(error.details = {json.dumps((run.get('recovery_error') or {}).get('details'))})."
        )
    return {
        "case_id": "C2",
        "name": "critical-order-infeasible",
        "mutation": f"quantity ORDER-001 (critical) x10: {original_quantity} -> {target['quantity']}.",
        "expectation": "status HARUS 'no-feasible-plan'.",
        "passed": passed,
        "actual_status": status,
        "constraint_violations": run.get("constraint_violations"),
        "findings": findings,
        "runs": [run],
    }


def case_c5(ctx: Context) -> dict[str, Any]:
    runs = [run_pipeline(ctx, data=copy.deepcopy(ctx.nominal), rainfall=rainfall) for rainfall in ("Q1", "Q4")]
    low, high = runs
    passed = all(
        run["actual_status"] in FEASIBLE_STATUSES and run.get("constraint_violations") == 0 for run in runs
    )
    sensitivity: dict[str, Any] = {}
    findings = []
    if all("kpis" in run for run in runs):
        sensitivity = {
            "relative_hazard_index": {
                "Q1": (low.get("hazard") or {}).get("relativeHazardIndex"),
                "Q4": (high.get("hazard") or {}).get("relativeHazardIndex"),
            },
            "route_exposure_counts": {"Q1": low["route_exposure_counts"], "Q4": high["route_exposure_counts"]},
            "kpi_delta_q4_minus_q1": {
                key: {
                    plan: round(high["kpis"][key][plan] - low["kpis"][key][plan], 4)
                    for plan in ("baseline", "recovery")
                }
                for key in KPI_KEYS
            },
        }
        delta = sensitivity["kpi_delta_q4_minus_q1"]
        findings.append(
            f"Relative hazard index Q1={sensitivity['relative_hazard_index']['Q1']} vs "
            f"Q4={sensitivity['relative_hazard_index']['Q4']}."
        )
        for plan in ("baseline", "recovery"):
            findings.append(
                f"{plan}: delta Q4-Q1 orders-fulfilled {delta['orders-fulfilled'][plan]:+g}, "
                f"failed-orders {delta['failed-orders'][plan]:+g}, "
                f"sales-exposure-risk {delta['sales-exposure-risk'][plan]:+,.0f} IDR."
            )
        if all(value == 0 for key in KPI_KEYS for value in delta[key].values()):
            findings.append("KPI identik antara Q1 dan Q4: output bisnis tidak sensitif terhadap skenario hazard.")
        statuses = {run["rainfall_scenario"]: run["actual_status"] for run in runs}
        if len(set(statuses.values())) > 1:
            findings.append(f"Status recovery berubah lintas hazard: {statuses}.")
    return {
        "case_id": "C5",
        "name": "hazard-sensitivity",
        "mutation": "Data nominal, dua simulasi: rainfall Q1 vs Q4.",
        "expectation": "kedua run ready/partial dengan 0 violation; dokumentasikan delta KPI lintas hazard.",
        "passed": passed,
        "actual_status": {run["rainfall_scenario"]: run["actual_status"] for run in runs},
        "constraint_violations": sum(run.get("constraint_violations") or 0 for run in runs),
        "sensitivity": sensitivity,
        "findings": findings,
        "runs": runs,
    }


CASES: tuple[tuple[str, Callable[[Context], dict[str, Any]]], ...] = (
    ("C1", case_c1),
    ("C2", case_c2),
    ("C5", case_c5),
)


def _run_case(case_id: str, case: Callable[[Context], dict[str, Any]], ctx: Context) -> dict[str, Any]:
    try:
        return case(ctx)
    except Exception as error:  # a broken case is recorded as a result, never a runner crash
        return {
            "case_id": case_id,
            "passed": False,
            "actual_status": "runner-error",
            "constraint_violations": None,
            "findings": [f"Runner error: {error!r}"],
            "traceback": traceback.format_exc(),
            "runs": [],
        }


def _print_table(results: list[dict[str, Any]], score: dict[str, Any]) -> None:
    header = f"{'case':<5}{'name':<28}{'status':<34}{'viol':>5}  {'fulfilled b->r':<16}{'pass':<5}"
    print(header)
    print("-" * len(header))
    for result in results:
        status = result["actual_status"]
        status_text = ",".join(f"{k}:{v}" for k, v in status.items()) if isinstance(status, dict) else str(status)
        fulfilled = []
        for run in result.get("runs", []):
            kpi = run.get("kpis", {}).get("orders-fulfilled")
            if kpi:
                fulfilled.append(f"{int(kpi['baseline'])}->{int(kpi['recovery'])}")
        violations = result.get("constraint_violations")
        print(
            f"{result['case_id']:<5}{result.get('name', ''):<28}{status_text:<34}"
            f"{'-' if violations is None else violations:>5}  {' '.join(fulfilled) or '-':<16}"
            f"{'PASS' if result['passed'] else 'FAIL':<5}"
        )
    print(
        f"\nBaseline score: {score['cases_passed']}/{score['cases_total']} = {score['score']:.2f}"
        f"  (pending: {', '.join(score['cases_pending'])})"
    )
    print("\nFindings:")
    for result in results:
        for finding in result.get("findings", []):
            print(f"  [{result['case_id']}] {finding}")


def main() -> int:
    nominal, data_source = load_nominal()
    simulation_repository.clear()
    business_snapshot_repository.clear()
    started = datetime.now()
    with TestClient(app, raise_server_exceptions=False) as client:
        ctx = Context(client, nominal, data_source)
        results = [_run_case(case_id, case, ctx) for case_id, case in CASES]
    passed = sum(bool(result["passed"]) for result in results)
    score = {
        "cases_passed": passed,
        "cases_total": len(results),
        "score": round(passed / len(results), 4) if results else 0.0,
        "cases_pending": list(PENDING_CASES),
    }
    output = {
        "suite": "aruna-phase1-baseline",
        "checkpoint": 1,
        "generated_at": started.isoformat(timespec="seconds"),
        "data_source": data_source,
        "scenario_id": ctx.scenario_id,
        "score": score,
        "findings": [
            {"case_id": result["case_id"], "finding": finding}
            for result in results
            for finding in result.get("findings", [])
        ],
        "cases": results,
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"baseline_{started:%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    _print_table(results, score)
    print(f"\nResults written to {path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
