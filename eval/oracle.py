"""Evaluation-only hindsight oracle.

The oracle sees actual demand, so it must never feed the decision system. It runs after the system
decision and answers: under the same testcase constraints (budget, MOQ, pack size, supplier capacity,
lead-time horizon, static storage check), what is the best any procurement plan could achieve?
Its purchases are replayed through the evaluation simulator so oracle numbers use exactly the same
fulfillment semantics as the system under test.
"""

from __future__ import annotations

import math
from typing import Any

from ortools.sat.python import cp_model

from eval.simulator import simulate

HORIZON_DAYS = 3


def _arrival_day(lead_time_hours: int) -> int:
    return max(1, math.ceil(lead_time_hours / 24))


def _build(output: dict[str, Any]) -> tuple[cp_model.CpModel, dict[str, Any], Any, Any]:
    params = output["input"]
    if len(set(output["ingredientByProduct"].values())) != len(output["productIds"]):
        raise ValueError("Oracle stock chain assumes one dedicated ingredient per product")
    recipe = params["recipeBasePerCup"]
    offers = [
        offer
        for offer in output["offers"]
        if offer["lead_time_hours"] <= HORIZON_DAYS * 24
    ]
    unit = math.gcd(
        recipe,
        params["initialStockBase"],
        params["storageCapacityBase"],
        *(offer["pack_quantity_base"] for offer in offers),
    )
    cup_units = recipe // unit
    model = cp_model.CpModel()
    packs: dict[str, Any] = {}
    served_terms = []
    cost_terms = []
    for product_id in output["productIds"]:
        ingredient_id = output["ingredientByProduct"][product_id]
        ingredient_offers = [o for o in offers if o["ingredient_id"] == ingredient_id]
        purchases = []
        arrivals: dict[int, list[Any]] = {day: [] for day in range(1, HORIZON_DAYS + 1)}
        for offer in ingredient_offers:
            count = model.new_int_var(0, offer["capacity_packs"], f"packs_{offer['id']}")
            selected = model.new_bool_var(f"selected_{offer['id']}")
            model.add(count == 0).only_enforce_if(selected.Not())
            model.add(count >= offer["minimum_packs"]).only_enforce_if(selected)
            packs[offer["id"]] = (offer, count)
            quantity = count * (offer["pack_quantity_base"] // unit)
            purchases.append(quantity)
            arrivals[_arrival_day(offer["lead_time_hours"])].append(quantity)
            cost_terms.append(count * offer["pack_cost_idr"])
        initial = params["initialStockBase"] // unit
        if purchases:
            model.add(initial + sum(purchases) <= params["storageCapacityBase"] // unit)
        stock: Any = initial
        for day in range(1, HORIZON_DAYS + 1):
            demand = output["actualDemand"][product_id][day - 1]
            served = model.new_int_var(0, demand, f"served_{product_id}_{day}")
            available = stock + sum(arrivals[day])
            model.add(served * cup_units <= available)
            stock = available - served * cup_units
            served_terms.append(served)
    if cost_terms:
        model.add(sum(cost_terms) <= params["budgetIdr"])
    return model, packs, sum(served_terms), sum(cost_terms)


def _solve(model: cp_model.CpModel) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.linearization_level = 2
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.solve(model)
    if status != cp_model.OPTIMAL:
        raise RuntimeError(f"Oracle did not prove optimality: {solver.status_name(status)}")
    return solver


def _replay(output: dict[str, Any], solver: cp_model.CpSolver, packs: dict[str, Any]) -> dict[str, Any]:
    decisions = []
    for offer, count in packs.values():
        value = solver.value(count)
        if value:
            decisions.append(
                {
                    "ingredientId": offer["ingredient_id"],
                    "offerId": offer["template_id"],
                    "supplierId": offer["supplier_id"],
                    "packCount": value,
                    "packQuantityBase": offer["pack_quantity_base"],
                    "quantityBase": value * offer["pack_quantity_base"],
                    "minimumPacks": offer["minimum_packs"],
                    "capacityPacks": offer["capacity_packs"],
                    "packCostIdr": offer["pack_cost_idr"],
                    "totalCostIdr": value * offer["pack_cost_idr"],
                    "leadTimeHours": offer["lead_time_hours"],
                }
            )
    simulation = simulate({**output, "decisions": decisions})
    if simulation["metrics"]["constraintViolations"]:
        raise RuntimeError("Oracle plan violated an evaluated constraint")
    return {"decisions": decisions, "metrics": simulation["metrics"]}


def oracle_diagnostics(output: dict[str, Any], system_metrics: dict[str, Any]) -> dict[str, Any]:
    """Hindsight bounds and regret for one executed case; diagnostic only."""
    if output["input"]["holdingCostIdrPerKgDay"] != 0:
        raise ValueError("Oracle cost model supports only the unevaluated zero holding rate")
    stockout_rate = output["input"]["stockoutCostIdrPerCup"]
    demand = sum(sum(values) for values in output["actualDemand"].values())

    # Oracle A: maximum fulfillment, then the cheapest plan that achieves it.
    model, packs, served, cost = _build(output)
    model.maximize(served)
    best_served = int(_solve(model).value(served))
    model.add(served >= best_served)
    model.minimize(cost)
    service_solver = _solve(model)
    service_oracle = _replay(output, service_solver, packs)

    # Oracle B: minimum total operational cost (purchase + stockout; holding and waste unevaluated).
    model, packs, served, cost = _build(output)
    model.minimize(cost + stockout_rate * (demand - served))
    cost_oracle = _replay(output, _solve(model), packs)

    oracle_max = service_oracle["metrics"]["fulfilledDemandCups"]
    if oracle_max != best_served:
        raise RuntimeError("Oracle replay disagrees with the oracle model")
    oracle_min_cost = cost_oracle["metrics"]["totalOperationalCostIdr"]
    system_fulfilled = system_metrics["fulfilledDemandCups"]
    return {
        "oracleMaximumFulfilledCups": oracle_max,
        "oracleServiceLevelPercent": round(oracle_max / demand * 100, 6) if demand else 100.0,
        "oracleCostAtMaximumFulfillmentIdr": service_oracle["metrics"]["totalOperationalCostIdr"],
        "oracleMinimumCostIdr": oracle_min_cost,
        "feasibleFulfillmentPercent": round(system_fulfilled / oracle_max * 100, 6) if oracle_max else None,
        "serviceRegretCups": oracle_max - system_fulfilled,
        "operationalCostRegretIdr": system_metrics["totalOperationalCostIdr"] - oracle_min_cost,
        "oracleDecisions": {
            "maximumFulfillment": service_oracle["decisions"],
            "minimumCost": cost_oracle["decisions"],
        },
        "note": "Hindsight oracle uses actual demand after the system decision; it never feeds decisions.",
    }
