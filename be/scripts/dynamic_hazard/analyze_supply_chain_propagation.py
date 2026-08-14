from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from app.repositories.simulation_repository import simulation_repository
from app.schemas.recovery import RecoveryResult
from app.schemas.simulation import InventoryOverride, RunSimulationRequest, VehicleOverride
from app.services.kpi_service import calculate_kpi
from app.services.recovery_service import BOM_SCALE, _material_availability, generate_recovery_plan
from app.services.simulation_service import create_simulation

BE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = BE_DIR / "artifacts" / "dynamic-hazard" / "experiments" / "phase5a"
SCENARIOS = ("Q1", "Q2", "Q3", "Q4")
CONDITION_ORDER = ("normal", "limited-vehicle", "critical-stock", "severe-disruption")
RISK_LEVELS = ("low", "medium", "high", "critical")

OPERATIONAL_CONDITIONS: dict[str, dict[str, Any]] = {
    "normal": {
        "label": "Normal",
        "vehicleOverrides": [],
        "inventoryOverrides": [],
    },
    "limited-vehicle": {
        "label": "Kendaraan Terbatas",
        "vehicleOverrides": [{"id": "V-03", "available": False}],
        "inventoryOverrides": [],
    },
    "critical-stock": {
        "label": "Stok Gudang Kritis",
        "vehicleOverrides": [],
        "inventoryOverrides": [
            {"facilityId": "wh-east", "productId": "prod-a", "quantity": 50},
            {"facilityId": "wh-west", "productId": "prod-a", "quantity": 50},
        ],
    },
    "severe-disruption": {
        "label": "Gangguan Operasional Berat",
        "vehicleOverrides": [
            {"id": "V-01", "available": False},
            {"id": "V-02", "available": False},
        ],
        "inventoryOverrides": [{"facilityId": "wh-east", "productId": "prod-a", "quantity": 0}],
    },
}

HISTORICAL_GOLDEN = {
    "roadResultsSha256": "08c150334871a0c3a2fb7a227516a3a533c03f00c813c38bcf4be9f1aa8c3afc",
    "routesSha256": "51039933930c8ce5536b937cb668ecb8367f088784284b91d93d08ea09de7740",
    "modelProvenanceSha256": "81b8d80227c4c048fbf657c827e096bf9938752867a18c66e7c8edf82464bf94",
}


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _hash_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _request(condition_id: str, scenario_id: str, *, historical: bool = False) -> RunSimulationRequest:
    condition = OPERATIONAL_CONDITIONS[condition_id]
    return RunSimulationRequest(
        scenario_id="scenario-jakarta-20250304",
        analysis_mode="historical-replay" if historical else "scenario-simulation",
        region="jakarta",
        rainfall_scenario=None if historical else scenario_id,
        vehicle_overrides=[VehicleOverride.model_validate(row) for row in condition["vehicleOverrides"]],
        inventory_overrides=[InventoryOverride.model_validate(row) for row in condition["inventoryOverrides"]],
    )


def _selected_routes(disruption: Any) -> dict[tuple[str, str], Any]:
    selected = {}
    for route in disruption.routes:
        selected[(route.origin_facility_id, route.destination_facility_id)] = route
    return selected


def _route_record(route: Any) -> dict[str, Any]:
    return {
        "origin": route.origin_facility_id,
        "destination": route.destination_facility_id,
        "routeType": route.type,
        "routeId": route.id,
        "distanceKm": route.distance_km,
        "etaMinutes": route.eta_minutes,
        "routingBand": route.flood_exposure,
        "dynamicRoadRiskScoreMaximum": route.flood_exposure_probability,
        "segmentCount": len(route.affected_road_segment_ids),
        "segmentPathSha256": hashlib.sha256("\n".join(route.affected_road_segment_ids).encode()).hexdigest(),
    }


def _recovery_record(recovery: RecoveryResult) -> dict[str, Any]:
    outcomes = sorted(recovery.recovery_order_outcomes, key=lambda row: row.order_id)
    production = {row.product_id: row.quantity for row in recovery.recovery_production}
    logistics = sorted(recovery.logistics_actions or [], key=lambda row: row.order_id)
    commerce = sorted(recovery.commerce_actions or [], key=lambda row: row.order_id)
    substitutions = [row.order_id for row in commerce if row.action in {"substitute", "split-substitute"}]
    delayed = [row.order_id for row in outcomes if row.delay_minutes > 0]
    failed = [row.order_id for row in outcomes if row.allocated_quantity == 0]
    partially_fulfilled = [row.order_id for row in outcomes if 0 < row.allocated_quantity < row.requested_quantity]
    assignments = [
        {
            "orderId": row.order_id,
            "requestedQuantity": row.requested_quantity,
            "allocatedQuantity": row.allocated_quantity,
            "warehouseId": row.warehouse_id,
            "vehicleId": row.vehicle_id,
            "routeId": row.route_id,
            "etaMinutes": row.eta_minutes,
            "deadlineMinutes": row.deadline_minutes,
            "delayMinutes": row.delay_minutes,
            "routingBand": row.flood_exposure,
        }
        for row in outcomes
    ]
    return {
        "solverStatus": recovery.status,
        "solverFeasible": recovery.status in {"ready", "partial"},
        "summary": recovery.summary.model_dump(mode="json", by_alias=True) if recovery.summary else None,
        "production": production,
        "assignments": assignments,
        "assignmentSha256": _hash_json(assignments),
        "vehicleAssignments": {row.order_id: row.vehicle_id for row in outcomes},
        "warehouseAssignments": {row.order_id: row.warehouse_id for row in outcomes},
        "routeAssignments": {row.order_id: row.route_id for row in outcomes},
        "substitutedOrders": substitutions,
        "delayedOrders": delayed,
        "failedOrders": failed,
        "partiallyFulfilledOrders": partially_fulfilled,
        "actionCounts": {
            "manufacturing": len(recovery.manufacturing_actions or []),
            "logistics": len(logistics),
            "commerce": len(commerce),
        },
        "logisticsActions": [
            {
                "orderId": row.order_id,
                "vehicleId": row.vehicle_id,
                "originalWarehouseId": row.original_warehouse_id,
                "recoveryWarehouseId": row.recovery_warehouse_id,
                "baselineRouteId": row.baseline_route_id,
                "recoveryRouteId": row.recovery_route_id,
                "baselineEtaMinutes": row.baseline_eta_minutes,
                "recoveryEtaMinutes": row.recovery_eta_minutes,
                "baselineRoutingBand": row.baseline_flood_exposure,
                "recoveryRoutingBand": row.recovery_flood_exposure,
                "action": row.action,
            }
            for row in logistics
        ],
        "commerceActions": {row.order_id: row.action for row in commerce},
    }


def _integrity_report(scenario: Any, disruption: Any, recovery: RecoveryResult) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    outcomes = recovery.recovery_order_outcomes
    order_index = {order.id: order for order in scenario.orders}
    product_index = {product.id: product for product in scenario.products}
    vehicle_index = {vehicle.id: vehicle for vehicle in scenario.vehicles if vehicle.available}
    route_ids = {route.id for route in disruption.routes}
    checks["solverFeasible"] = recovery.status in {"ready", "partial"}
    checks["oneOutcomePerOrder"] = len(outcomes) == len(order_index) == len({row.order_id for row in outcomes})
    checks["quantitiesValid"] = all(
        0 <= row.allocated_quantity <= row.requested_quantity == order_index[row.order_id].quantity for row in outcomes
    )
    checks["noNegativeTimeOrValue"] = all(
        row.delay_minutes >= 0 and row.allocated_value >= 0 and (row.eta_minutes is None or row.eta_minutes >= 0)
        for row in outcomes
    )
    checks["routeAssignmentsValid"] = all(row.route_id is None or row.route_id in route_ids for row in outcomes)
    checks["vehicleAvailabilityRespected"] = all(
        row.vehicle_id is None or row.vehicle_id in vehicle_index for row in outcomes
    )
    vehicle_loads = Counter()
    for row in outcomes:
        if row.vehicle_id:
            vehicle_loads[row.vehicle_id] += row.allocated_quantity
    checks["vehicleCapacityRespected"] = all(
        quantity <= vehicle_index[vehicle_id].capacity_units for vehicle_id, quantity in vehicle_loads.items()
    )
    checks["criticalOrdersFulfilled"] = all(
        row.allocated_quantity == row.requested_quantity
        for row in outcomes
        if order_index[row.order_id].priority == "critical"
    )
    production = {row.product_id: row.quantity for row in recovery.recovery_production}
    factory_capacity = sum(
        facility.production_capacity_units or 0 for facility in scenario.facilities if facility.kind == "factory"
    )
    checks["factoryCapacityRespected"] = (
        all(value >= 0 for value in production.values()) and sum(production.values()) <= factory_capacity
    )
    available_material = _material_availability(scenario, disruption, baseline=False)
    material_use = Counter()
    for product_id, quantity in production.items():
        for item in product_index[product_id].bom:
            material_use[item.material_id] += quantity * round(item.quantity_per_unit * BOM_SCALE)
    checks["bomAndMaterialAvailabilityRespected"] = all(
        used <= round(available_material[material_id] * BOM_SCALE) for material_id, used in material_use.items()
    )
    inventory = Counter({(item.facility_id, item.product_id): round(item.quantity) for item in scenario.inventory})
    product_allocations = Counter()
    commerce = {row.order_id: row for row in recovery.commerce_actions or []}
    for outcome in outcomes:
        if outcome.warehouse_id is None:
            continue
        for allocation in commerce[outcome.order_id].allocations:
            product_allocations[outcome.warehouse_id, allocation.product_id] += allocation.quantity
    checks["warehouseInventoryPlusProductionUpperBound"] = all(
        allocated <= inventory[warehouse_id, product_id] + production.get(product_id, 0)
        for (warehouse_id, product_id), allocated in product_allocations.items()
    )
    checks["delayCalculationConsistent"] = all(
        row.delay_minutes == max(0, (row.eta_minutes or row.deadline_minutes) - row.deadline_minutes)
        for row in outcomes
    )
    return {"allPassed": all(checks.values()), "checks": checks}


def _kpi_record(kpi: Any) -> dict[str, Any]:
    return {
        row.key: {
            "baseline": row.baseline,
            "recovery": row.recovery,
            "total": row.total,
            "currency": row.currency,
        }
        for row in kpi.metrics
    }


def _historical_regression() -> dict[str, Any]:
    simulation_repository.clear()
    simulation = create_simulation(_request("normal", "Q1", historical=True))
    disruption = simulation_repository.get_disruption(simulation.id)
    scenario = simulation_repository.get_effective_scenario(simulation.id)
    recovery = generate_recovery_plan(simulation.id, scenario, disruption, None)
    kpi = calculate_kpi(simulation.id, scenario, recovery)
    roads = [
        (road.segment_id, road.risk_probability, road.risk_level, road.estimated_delay_minutes)
        for road in disruption.roads
    ]
    routes = [
        (
            route.type,
            route.origin_facility_id,
            route.destination_facility_id,
            route.affected_road_segment_ids,
            route.eta_minutes,
            route.flood_exposure,
            route.flood_exposure_probability,
        )
        for route in disruption.routes
    ]
    provenance = simulation.model_provenance.model_dump(mode="json")
    actual = {
        "roadResultsSha256": _hash_json(roads),
        "routesSha256": _hash_json(routes),
        "modelProvenanceSha256": _hash_json(provenance),
    }
    recovery_record = _recovery_record(recovery)
    canonical_recovery = {
        "solverStatus": recovery_record["solverStatus"],
        "production": recovery_record["production"],
        "assignments": recovery_record["assignments"],
        "actionCounts": recovery_record["actionCounts"],
    }
    return {
        "goldenExpected": HISTORICAL_GOLDEN,
        "goldenActual": actual,
        "goldenMatches": actual == HISTORICAL_GOLDEN,
        "dynamicHazardAbsent": simulation.hazard is None
        and all(road.dynamic_road_risk_score is None for road in disruption.roads),
        "recoveryCanonicalSha256": _hash_json(canonical_recovery),
        "kpiCanonicalSha256": _hash_json(_kpi_record(kpi)),
        "recovery": canonical_recovery,
        "kpi": _kpi_record(kpi),
    }


def _run_combination(condition_id: str, scenario_id: str) -> dict[str, Any]:
    request = _request(condition_id, scenario_id)
    simulation = create_simulation(request)
    disruption = simulation_repository.get_disruption(simulation.id)
    effective_scenario = simulation_repository.get_effective_scenario(simulation.id)
    recovery = generate_recovery_plan(simulation.id, effective_scenario, disruption, None)
    kpi = calculate_kpi(simulation.id, effective_scenario, recovery)
    scores = np.asarray([road.dynamic_road_risk_score for road in disruption.roads], dtype=np.float64)
    levels = Counter(road.risk_level for road in disruption.roads)
    selected_routes = _selected_routes(disruption)
    available_vehicles = sorted(vehicle.id for vehicle in effective_scenario.vehicles if vehicle.available)
    inventory = {f"{item.facility_id}:{item.product_id}": item.quantity for item in effective_scenario.inventory}
    return {
        "conditionId": condition_id,
        "conditionLabel": OPERATIONAL_CONDITIONS[condition_id]["label"],
        "rainfallScenario": scenario_id,
        "request": request.model_dump(mode="json", by_alias=True),
        "hazard": simulation.hazard.model_dump(mode="json", by_alias=True),
        "operationalState": {"availableVehicleIds": available_vehicles, "inventory": inventory},
        "roadRisk": {
            "count": len(scores),
            "routingBandCounts": {level: levels.get(level, 0) for level in RISK_LEVELS},
            "minimum": float(scores.min()),
            "median": float(np.median(scores)),
            "p90": float(np.quantile(scores, 0.90)),
            "p95": float(np.quantile(scores, 0.95)),
            "maximum": float(scores.max()),
            "scoreMapSha256": hashlib.sha256(scores.tobytes(order="C")).hexdigest(),
        },
        "routing": {
            "odPairCount": len(selected_routes),
            "unreachableCount": 12 - len(selected_routes),
            "selectedRoutes": [_route_record(selected_routes[pair]) for pair in sorted(selected_routes)],
        },
        "disruption": {
            "affectedSupplierIds": disruption.impact.impacted_supplier_ids,
            "affectedWarehouseIds": disruption.impact.impacted_warehouse_ids,
            "affectedOrderIds": disruption.impact.impacted_order_ids,
            "roadSegmentsAtRisk": disruption.impact.road_segments_at_risk,
            "salesExposure": disruption.impact.sales_exposure.model_dump(mode="json", by_alias=True),
            "issueCount": len(disruption.impact.issues),
        },
        "recovery": _recovery_record(recovery),
        "kpi": _kpi_record(kpi),
        "optimizerIntegrity": _integrity_report(effective_scenario, disruption, recovery),
    }


def _diff_map(lower: dict[str, Any], upper: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set(lower) | set(upper))
    return {key: {"from": lower.get(key), "to": upper.get(key)} for key in keys if lower.get(key) != upper.get(key)}


def _trace(condition_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    q1 = condition_rows[0]
    q1_routes = {(row["origin"], row["destination"]): row for row in q1["routing"]["selectedRoutes"]}
    traces = []
    for row in condition_rows:
        routes = {(item["origin"], item["destination"]): item for item in row["routing"]["selectedRoutes"]}
        route_changes = [
            {
                "origin": pair[0],
                "destination": pair[1],
                "q1PathSha256": q1_routes[pair]["segmentPathSha256"],
                "scenarioPathSha256": routes[pair]["segmentPathSha256"],
                "etaChangeMinutes": routes[pair]["etaMinutes"] - q1_routes[pair]["etaMinutes"],
                "routingBand": {"from": q1_routes[pair]["routingBand"], "to": routes[pair]["routingBand"]},
            }
            for pair in sorted(routes)
            if routes[pair]["segmentPathSha256"] != q1_routes[pair]["segmentPathSha256"]
        ]
        production_changes = _diff_map(q1["recovery"]["production"], row["recovery"]["production"])
        assignment_changes = [
            {
                "orderId": current["orderId"],
                "from": baseline,
                "to": current,
            }
            for baseline, current in zip(q1["recovery"]["assignments"], row["recovery"]["assignments"], strict=True)
            if baseline != current
        ]
        kpi_changes = {
            key: {"from": q1["kpi"][key]["recovery"], "to": value["recovery"]}
            for key, value in row["kpi"].items()
            if value["recovery"] != q1["kpi"][key]["recovery"]
        }
        if kpi_changes or production_changes:
            binding = "BINDING"
            reason = "Hazard changes reach production and/or KPI outcomes through existing constraints."
        elif assignment_changes:
            binding = "PARTIALLY_BINDING"
            reason = "Routing/CP-SAT decisions change, but headline KPI remains buffered by operational slack."
        else:
            binding = "NON_BINDING"
            reason = "Hazard state changes do not alter the selected recovery plan relative to Q1."
        if row["rainfallScenario"] == "Q1":
            binding = "NON_BINDING"
            reason = "Q1 is the within-condition reference for incremental binding analysis."
        traces.append(
            {
                "conditionId": row["conditionId"],
                "rainfallScenario": row["rainfallScenario"],
                "classification": binding,
                "reason": reason,
                "causalChain": {
                    "hazard": row["hazard"],
                    "roadRiskMedian": row["roadRisk"]["median"],
                    "routingChangesFromQ1": route_changes,
                    "disruptionChangesFromQ1": {
                        "affectedSupplierIds": {
                            "from": q1["disruption"]["affectedSupplierIds"],
                            "to": row["disruption"]["affectedSupplierIds"],
                        },
                        "roadSegmentsAtRisk": {
                            "from": q1["disruption"]["roadSegmentsAtRisk"],
                            "to": row["disruption"]["roadSegmentsAtRisk"],
                        },
                    },
                    "productionChanges": production_changes,
                    "assignmentChanges": assignment_changes,
                    "kpiChanges": kpi_changes,
                },
            }
        )
    return traces


def _write_csv(path: Path, rows: list[dict[str, Any]], traces: list[dict[str, Any]]) -> None:
    trace_index = {(row["conditionId"], row["rainfallScenario"]): row for row in traces}
    fields = [
        "conditionId",
        "rainfallScenario",
        "temporalHazardScore",
        "relativeHazardIndex",
        "roadRiskMedian",
        "roadRiskP90",
        "roadRiskP95",
        "low",
        "medium",
        "high",
        "critical",
        "routesChangedVsQ1",
        "affectedSuppliers",
        "affectedWarehouses",
        "affectedOrders",
        "solverStatus",
        "prodA",
        "prodB",
        "ordersFulfilled",
        "onTimeDelivery",
        "failedOrders",
        "averageDelay",
        "salesExposureRisk",
        "bindingClassification",
        "optimizerIntegrityPassed",
    ]
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            trace = trace_index[row["conditionId"], row["rainfallScenario"]]
            counts = row["roadRisk"]["routingBandCounts"]
            metrics = row["kpi"]
            writer.writerow(
                {
                    "conditionId": row["conditionId"],
                    "rainfallScenario": row["rainfallScenario"],
                    "temporalHazardScore": row["hazard"]["temporalHazardScore"],
                    "relativeHazardIndex": row["hazard"]["relativeHazardIndex"],
                    "roadRiskMedian": row["roadRisk"]["median"],
                    "roadRiskP90": row["roadRisk"]["p90"],
                    "roadRiskP95": row["roadRisk"]["p95"],
                    **counts,
                    "routesChangedVsQ1": len(trace["causalChain"]["routingChangesFromQ1"]),
                    "affectedSuppliers": len(row["disruption"]["affectedSupplierIds"]),
                    "affectedWarehouses": len(row["disruption"]["affectedWarehouseIds"]),
                    "affectedOrders": len(row["disruption"]["affectedOrderIds"]),
                    "solverStatus": row["recovery"]["solverStatus"],
                    "prodA": row["recovery"]["production"].get("prod-a", 0),
                    "prodB": row["recovery"]["production"].get("prod-b", 0),
                    "ordersFulfilled": metrics["orders-fulfilled"]["recovery"],
                    "onTimeDelivery": metrics["on-time-delivery"]["recovery"],
                    "failedOrders": metrics["failed-orders"]["recovery"],
                    "averageDelay": metrics["average-delay"]["recovery"],
                    "salesExposureRisk": metrics["sales-exposure-risk"]["recovery"],
                    "bindingClassification": trace["classification"],
                    "optimizerIntegrityPassed": row["optimizerIntegrity"]["allPassed"],
                }
            )


def run_analysis(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    simulation_repository.clear()
    rows = []
    for condition_id in CONDITION_ORDER:
        for scenario_id in SCENARIOS:
            rows.append(_run_combination(condition_id, scenario_id))
    traces = []
    for condition_id in CONDITION_ORDER:
        traces.extend(_trace([row for row in rows if row["conditionId"] == condition_id]))
    hazard_by_scenario = {
        scenario_id: {
            (row["hazard"]["temporalHazardScore"], row["hazard"]["relativeHazardIndex"])
            for row in rows
            if row["rainfallScenario"] == scenario_id
        }
        for scenario_id in SCENARIOS
    }
    hazard_independent = all(len(values) == 1 for values in hazard_by_scenario.values())
    operational_independent = all(
        row["operationalState"]
        == next(candidate["operationalState"] for candidate in rows if candidate["conditionId"] == row["conditionId"])
        for row in rows
    )
    historical = _historical_regression()
    matrix = {
        "analysisVersion": "dynamic-hazard-phase5a-v1",
        "researchOnly": True,
        "combinationCount": len(rows),
        "rainfallScenarios": list(SCENARIOS),
        "operationalConditions": OPERATIONAL_CONDITIONS,
        "recoveryConstraints": {
            "allowSubstitution": False,
            "maxAdditionalDelayMinutes": None,
        },
        "routingToOptimizerContract": {
            "routeSelection": "Recovery route when available, otherwise baseline route",
            "criticalBandEffect": "Critical recovery routes are excluded from feasible route options",
            "etaEffect": "ETA controls deadline delay and optional maximum-additional-delay feasibility",
            "riskEffect": "Routing-band rank contributes an existing CP-SAT objective penalty",
            "distanceEffect": "Route distance and vehicle cost contribute an existing transport penalty",
            "supplierEffect": (
                "Baseline supplier-route routing band scales material availability before BOM constraints"
            ),
            "routeIdOnly": False,
        },
        "independence": {
            "hazardIndependentOfOperationalCondition": hazard_independent,
            "operationalStateIndependentOfRainfallScenario": operational_independent,
        },
        "historicalRegression": historical,
        "rows": rows,
    }
    classifications = Counter(row["classification"] for row in traces)
    any_binding = classifications["BINDING"] > 0
    all_integrity = all(row["optimizerIntegrity"]["allPassed"] for row in rows)
    core_checks_pass = (
        len(rows) == 16
        and all_integrity
        and historical["goldenMatches"]
        and historical["dynamicHazardAbsent"]
        and hazard_independent
        and operational_independent
    )
    if not core_checks_pass or not any_binding:
        decision = "NO-GO"
    elif classifications["PARTIALLY_BINDING"] > 0:
        decision = "CONDITIONAL GO"
    else:
        decision = "GO"
    gate = {
        "decision": decision,
        "nextPhase": "Phase 5B - Frontend Dynamic Scenario Integration",
        "checks": {
            "fullBackendFlowWorks": len(rows) == 16,
            "atLeastOneBusinessBindingEffect": any_binding,
            "allOptimizerIntegrityChecksPass": all_integrity,
            "historicalGoldenMatches": historical["goldenMatches"],
            "historicalDynamicMetadataAbsent": historical["dynamicHazardAbsent"],
            "hazardOperationalIndependence": hazard_independent and operational_independent,
        },
        "bindingCounts": dict(classifications),
        "reason": (
            "The existing backend produces real explainable binding effects for several scenarios, while some "
            "scenario/condition combinations remain partially or non-binding because discrete routing, inventory, "
            "and vehicle slack absorb the hazard change. Frontend wording must not imply monotonic KPI impact."
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _save_json(output_dir / "propagation_matrix.json", matrix)
    _save_json(output_dir / "causal_traces.json", {"analysisVersion": matrix["analysisVersion"], "traces": traces})
    _save_json(output_dir / "decision_gate.json", gate)
    _write_csv(output_dir / "propagation_matrix.csv", rows, traces)
    simulation_repository.clear()
    return {"matrix": matrix, "traces": traces, "decisionGate": gate}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate end-to-end dynamic hazard supply-chain propagation.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_analysis(args.output_dir)
    print(json.dumps(result["decisionGate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
