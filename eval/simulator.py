from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from eval.metrics import forecast_diagnostics, operational_metrics


def _check_constraints(output: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    violations: list[dict[str, Any]] = []
    checks = 0
    purchases: dict[str, int] = defaultdict(int)
    total_cost = 0
    for decision in output["decisions"]:
        checks += 6
        packs = decision["packCount"]
        if not isinstance(packs, int) or packs < 0:
            violations.append(
                {"rule": "integer-nonnegative-packs", "decision": decision}
            )
        if packs and packs < decision["minimumPacks"]:
            violations.append({"rule": "moq", "decision": decision})
        if packs > decision["capacityPacks"]:
            violations.append({"rule": "supplier-capacity", "decision": decision})
        if decision["quantityBase"] != packs * decision["packQuantityBase"]:
            violations.append({"rule": "pack-multiple", "decision": decision})
        if decision["leadTimeHours"] > 72:
            violations.append({"rule": "arrival-outside-horizon", "decision": decision})
        if decision["totalCostIdr"] != packs * decision["packCostIdr"]:
            violations.append({"rule": "cost-arithmetic", "decision": decision})
        purchases[decision["ingredientId"]] += decision["quantityBase"]
        total_cost += decision["totalCostIdr"]

    checks += 1
    if total_cost > output["input"]["budgetIdr"]:
        violations.append(
            {
                "rule": "shared-budget",
                "actual": total_cost,
                "limit": output["input"]["budgetIdr"],
            }
        )
    for ingredient_id, quantity in purchases.items():
        checks += 1
        projected = output["input"]["initialStockBase"] + quantity
        if projected > output["input"]["storageCapacityBase"]:
            violations.append(
                {
                    "rule": "storage-capacity",
                    "ingredientId": ingredient_id,
                    "actual": projected,
                    "limit": output["input"]["storageCapacityBase"],
                }
            )
    return violations, checks


def simulate(output: dict[str, Any]) -> dict[str, Any]:
    stocks = {
        ingredient_id: output["input"]["initialStockBase"]
        for ingredient_id in output["ingredientByProduct"].values()
    }
    arrivals: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for decision in output["decisions"]:
        arrival_day = max(1, math.ceil(decision["leadTimeHours"] / 24))
        arrivals[arrival_day].append(decision)

    demanded_cups = 0
    fulfilled_cups = 0
    holding_cost_idr = 0
    daily = []
    for day_index in (1, 2, 3):
        for decision in arrivals[day_index]:
            stocks[decision["ingredientId"]] += decision["quantityBase"]
        day_demand = 0
        day_fulfilled = 0
        for product_id in output["productIds"]:
            demand = output["actualDemand"][product_id][day_index - 1]
            ingredient_id = output["ingredientByProduct"][product_id]
            possible = stocks[ingredient_id] // output["input"]["recipeBasePerCup"]
            fulfilled = min(demand, possible)
            stocks[ingredient_id] -= fulfilled * output["input"]["recipeBasePerCup"]
            day_demand += demand
            day_fulfilled += fulfilled
        demanded_cups += day_demand
        fulfilled_cups += day_fulfilled
        ending_stock_kg = sum(stocks.values()) / 1_000_000
        day_holding_cost = round(
            ending_stock_kg * output["input"]["holdingCostIdrPerKgDay"]
        )
        holding_cost_idr += day_holding_cost
        daily.append(
            {
                "day": day_index,
                "demandedCups": day_demand,
                "fulfilledCups": day_fulfilled,
                "unfulfilledCups": day_demand - day_fulfilled,
                "endingStockKg": round(ending_stock_kg, 6),
                "holdingCostIdr": day_holding_cost,
            }
        )

    violations, checks = _check_constraints(output)
    predicted = [
        value
        for product_id in output["productIds"]
        for value in output["predictions"][product_id]
    ]
    actual = [
        value
        for product_id in output["productIds"]
        for value in output["actualDemand"][product_id]
    ]
    unfulfilled_cups = demanded_cups - fulfilled_cups
    metrics = operational_metrics(
        demanded_cups=demanded_cups,
        fulfilled_cups=fulfilled_cups,
        purchase_cost_idr=sum(
            decision["totalCostIdr"] for decision in output["decisions"]
        ),
        holding_cost_idr=holding_cost_idr,
        stockout_cost_idr=unfulfilled_cups * output["input"]["stockoutCostIdrPerCup"],
        waste_cost_idr=0,
        violations=violations,
        constraint_checks=checks,
    )
    return {
        "daily": daily,
        "endingStockBase": stocks,
        "metrics": metrics,
        "forecastDiagnostics": forecast_diagnostics(predicted, actual),
        "waste": {
            "evaluated": False,
            "reason": "Shelf-life and lot-age data are unavailable; waste is not fabricated.",
        },
        "holdingCost": {
            "evaluated": output["input"]["holdingCostIdrPerKgDay"] > 0,
            "rateIdrPerKgDay": output["input"]["holdingCostIdrPerKgDay"],
            "reason": "No validated holding-cost rate is available."
            if output["input"]["holdingCostIdrPerKgDay"] == 0
            else None,
        },
    }
