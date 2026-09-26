from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from ortools.sat.python import cp_model

from app.errors import ApiError

OPTIMIZER_VERSION = "time-indexed-lexicographic-v2"
HORIZON_DAYS = 3
# Lost-sales weights are micro-IDR per base unit so fractional IDR/base rates stay integral.
LOST_SALES_SCALE = 1_000_000
STAGES = ("SERVICE", "URGENCY", "SAFETY", "COST")


def map_solver_status(status: cp_model.CpSolverStatus) -> str:
    if status == cp_model.OPTIMAL:
        return "OPTIMAL"
    if status == cp_model.FEASIBLE:
        return "FEASIBLE"
    if status == cp_model.INFEASIBLE:
        return "INFEASIBLE"
    return "ERROR"


def default_arrival_day(lead_time_hours: int) -> int:
    """Evaluation semantics: an order placed at the close of the as-of day lands at the start of a day."""
    return max(1, math.ceil(lead_time_hours / 24))


def _quantity_unit(base: dict[str, Any], daily_incoming: list[int], offers: list[dict[str, Any]]) -> int:
    """Largest exact unit dividing every quantity of one ingredient, keeping CP-SAT domains small."""
    values = [*base["dailyRequired"], max(0, base["current"]), base["safety"], *daily_incoming]
    values.extend(offer["pack_quantity_base"] for offer in offers)
    if base["storageCapacity"] is not None:
        values.append(base["storageCapacity"])
    return math.gcd(*(int(value) for value in values)) or 1


def _lost_sales_weights(risks: list[dict[str, Any]], units: dict[str, int]) -> dict[str, int]:
    """Integer lost-sales value per scaled quantity unit, comparable across ingredients."""
    raw = {
        risk["ingredientId"]: max(
            1,
            round(float(risk["_base"].get("lostSalesIdrPerBase", 0)) * units[risk["ingredientId"]] * LOST_SALES_SCALE),
        )
        for risk in risks
    }
    divisor = math.gcd(*raw.values()) if raw else 1
    return {ingredient_id: weight // divisor for ingredient_id, weight in raw.items()}


def optimize_procurement(
    *,
    risks: list[dict[str, Any]],
    offers: list[dict[str, Any]],
    budget_idr: int,
    reserved_cost_idr: int = 0,
    incoming_by_day: dict[str, dict[int, int]] | None = None,
    arrival_day_by_offer: dict[str, int] | None = None,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    """Run the time-indexed CP-SAT decision model without persistence concerns.

    Each ingredient keeps a daily inventory balance over the three-day horizon. Offers are credited
    only on their arrival day. Storage is enforced without crediting forecast consumption, so the
    plan stays physically feasible even when actual demand is lower than predicted. Objectives are
    optimized sequentially: lost-sales value, urgency tie-break, ending safety deficit, purchase cost.
    """
    incoming = incoming_by_day or {}
    arrival_overrides = arrival_day_by_offer or {}
    available_budget = max(0, budget_idr - reserved_cost_idr)
    days = range(1, HORIZON_DAYS + 1)
    by_ingredient: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for offer in offers:
        by_ingredient[offer["ingredient_id"]].append(offer)
    arrival_days: dict[str, int] = {}
    eligible: dict[str, list[dict[str, Any]]] = {}
    incoming_rows: dict[str, list[int]] = {}
    units: dict[str, int] = {}
    targets: dict[str, int] = {}
    limitations: list[str] = []
    for risk in risks:
        ingredient_id = risk["ingredientId"]
        base = risk["_base"]
        if len(base["dailyRequired"]) != HORIZON_DAYS:
            raise ValueError(f"dailyRequired for {ingredient_id} must cover {HORIZON_DAYS} days")
        daily_incoming = [int(incoming.get(ingredient_id, {}).get(day, 0)) for day in days]
        if any(daily_incoming):
            limitations.append(f"APPROVED_QUANTITY_UNCONFIRMED:{ingredient_id}:{sum(daily_incoming)}")
        targets[ingredient_id] = max(
            0, sum(base["dailyRequired"]) + base["safety"] - max(0, base["current"]) - sum(daily_incoming)
        )
        relevant = []
        for offer in by_ingredient.get(ingredient_id, []):
            arrival_day = arrival_overrides.get(offer["id"], default_arrival_day(offer["lead_time_hours"]))
            if offer["lead_time_hours"] <= HORIZON_DAYS * 24 and 1 <= arrival_day <= HORIZON_DAYS:
                relevant.append(offer)
                arrival_days[offer["id"]] = arrival_day
        if not relevant and targets[ingredient_id] > 0:
            limitations.append(f"NO_ELIGIBLE_SUPPLIER_WITHIN_HORIZON:{ingredient_id}")
        eligible[ingredient_id] = relevant
        incoming_rows[ingredient_id] = daily_incoming
        units[ingredient_id] = _quantity_unit(base, daily_incoming, relevant)
    weights = _lost_sales_weights(risks, units)
    risk_count = len(risks)

    model = cp_model.CpModel()
    pack_vars: dict[str, Any] = {}
    shortage_vars: dict[str, list[Any]] = {}
    inventory_vars: dict[str, list[Any]] = {}
    deficit_vars: dict[str, Any] = {}
    cost_terms = []
    service_terms = []
    urgency_terms = []
    safety_terms = []
    for risk in risks:
        ingredient_id = risk["ingredientId"]
        base = risk["_base"]
        unit = units[ingredient_id]
        weight = weights[ingredient_id]
        daily_required = [int(value) // unit for value in base["dailyRequired"]]
        daily_incoming = [value // unit for value in incoming_rows[ingredient_id]]
        current = max(0, int(base["current"])) // unit
        safety = int(base["safety"]) // unit

        arrivals_by_day: dict[int, list[Any]] = defaultdict(list)
        max_purchase = 0
        for offer in eligible[ingredient_id]:
            capacity_packs = offer["capacity_packs"]
            if capacity_packs is None:
                raise ApiError(
                    422,
                    "MISSING_PROCUREMENT_CONSTRAINT",
                    "Supplier capacity harus dikonfigurasi untuk optimizer.",
                    details={"offerId": offer["id"], "field": "capacity"},
                )
            pack_units = offer["pack_quantity_base"] // unit
            packs = model.new_int_var(0, capacity_packs, f"packs_{offer['id']}")
            selected = model.new_bool_var(f"selected_{offer['id']}")
            model.add(packs == 0).only_enforce_if(selected.Not())
            model.add(packs >= offer["minimum_packs"]).only_enforce_if(selected)
            pack_vars[offer["id"]] = packs
            arrivals_by_day[arrival_days[offer["id"]]].append(packs * pack_units)
            cost_terms.append(packs * offer["pack_cost_idr"])
            max_purchase += capacity_packs * pack_units

        storage_capacity = None if base["storageCapacity"] is None else int(base["storageCapacity"]) // unit
        cumulative_incoming = 0
        cumulative_purchase = []
        upper = current + sum(daily_incoming) + max_purchase
        previous: Any = current
        shortages = []
        inventories = []
        # Rank 1 is most urgent; earlier days weigh more so unavoidable gaps are pushed later.
        priority_weight = risk_count - int(base.get("priorityRank", risk_count)) + 1
        for day, required, arriving in zip(days, daily_required, daily_incoming, strict=True):
            purchased_today = arrivals_by_day.get(day, [])
            cumulative_purchase.extend(purchased_today)
            cumulative_incoming += arriving
            if storage_capacity is not None and cumulative_purchase:
                room = max(0, storage_capacity - current - cumulative_incoming)
                model.add(sum(cumulative_purchase) <= room)
            served = model.new_int_var(0, required, f"served_{ingredient_id}_{day}")
            shortage = model.new_int_var(0, required, f"shortage_{ingredient_id}_{day}")
            inventory = model.new_int_var(0, upper, f"inventory_{ingredient_id}_{day}")
            model.add(shortage == required - served)
            model.add(inventory == previous + arriving + sum(purchased_today) - served)
            shortages.append(shortage)
            inventories.append(inventory)
            previous = inventory
            service_terms.append(shortage * weight)
            urgency_terms.append(shortage * weight * priority_weight * (HORIZON_DAYS - day + 1))
        deficit = model.new_int_var(0, safety, f"safety_deficit_{ingredient_id}")
        model.add(deficit >= safety - inventories[-1])
        safety_terms.append(deficit * weight)
        shortage_vars[ingredient_id] = shortages
        inventory_vars[ingredient_id] = inventories
        deficit_vars[ingredient_id] = deficit
    if cost_terms:
        model.add(sum(cost_terms) <= available_budget)

    objectives = {
        "SERVICE": sum(service_terms),
        "URGENCY": sum(urgency_terms),
        "SAFETY": sum(safety_terms),
        "COST": sum(cost_terms),
    }
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds / len(STAGES)
    solver.parameters.num_search_workers = 1
    # Full LP relaxation lets the single deterministic worker prove each stage optimal quickly;
    # at the default level the tie-break and cost stages stall at FEASIBLE.
    solver.parameters.linearization_level = 2
    stage_statuses: dict[str, str] = {}
    stage_values: dict[str, int] = {}
    solution: dict[str, Any] | None = None
    first_status = None
    for stage in STAGES:
        objective = objectives[stage]
        model.minimize(objective)
        status = solver.solve(model)
        stage_statuses[stage] = solver.status_name(status)
        if first_status is None:
            first_status = status
        if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
            break
        # Read the objective exactly as an integer; float objective_value loses precision above 2**53.
        value = int(solver.value(objective)) if not isinstance(objective, int) else objective
        stage_values[stage] = value
        if not isinstance(objective, int):
            model.add(objective <= value)
        solution = _read_solution(solver, units, pack_vars, shortage_vars, inventory_vars, deficit_vars)
        # A complete hint makes the previous stage optimum an immediate incumbent for the next stage.
        model.clear_hints()
        for index in range(len(model.proto.variables)):
            handle = model.get_int_var_from_proto_index(index)
            model.add_hint(handle, solver.value(handle))

    if solution is not None:
        all_optimal = len(stage_values) == len(STAGES) and all(
            stage_statuses[stage] == "OPTIMAL" for stage in STAGES
        )
        optimizer_status = "OPTIMAL" if all_optimal else "FEASIBLE"
        status_detail = "OPTIMAL" if all_optimal else ";".join(f"{k}={v}" for k, v in stage_statuses.items())
        selected_offers = [
            {"offer": offer, "packs": solution["packs"][offer["id"]], "arrivalDay": arrival_days[offer["id"]]}
            for offer in offers
            if solution["packs"].get(offer["id"], 0) > 0
        ]
        unmet = {
            ingredient_id: sum(solution["shortages"][ingredient_id]) + solution["deficits"][ingredient_id]
            for ingredient_id in shortage_vars
        }
        plan_outcome = "COMPLETE" if not any(unmet.values()) else "PARTIAL"
        daily_plan = _daily_plan(risks, incoming, selected_offers, solution)
        limitations.extend(_timing_limitations(risks, arrival_days, by_ingredient, solution))
    else:
        optimizer_status = map_solver_status(first_status)
        status_detail = ";".join(f"{k}={v}" for k, v in stage_statuses.items())
        selected_offers = []
        unmet = targets
        plan_outcome = "INFEASIBLE"
        daily_plan = {}

    total_cost = sum(item["offer"]["pack_cost_idr"] * item["packs"] for item in selected_offers)
    return {
        "optimizerStatus": optimizer_status,
        "solverStatusDetail": status_detail,
        "planOutcome": plan_outcome,
        "selectedOffers": selected_offers,
        "unmet": unmet,
        "targets": targets,
        "limitations": limitations,
        "totalEstimatedCost": total_cost,
        "availableBudget": available_budget,
        "optimizerVersion": OPTIMIZER_VERSION,
        "objectiveStages": [
            {"stage": stage, "status": stage_statuses.get(stage), "value": stage_values.get(stage)} for stage in STAGES
        ],
        "dailyPlan": daily_plan,
    }


def _read_solution(solver, units, pack_vars, shortage_vars, inventory_vars, deficit_vars) -> dict[str, Any]:
    """Solver values converted back from scaled units to base units."""
    return {
        "packs": {offer_id: solver.value(variable) for offer_id, variable in pack_vars.items()},
        "shortages": {key: [solver.value(v) * units[key] for v in values] for key, values in shortage_vars.items()},
        "inventories": {
            key: [solver.value(v) * units[key] for v in values] for key, values in inventory_vars.items()
        },
        "deficits": {key: solver.value(variable) * units[key] for key, variable in deficit_vars.items()},
    }


def _daily_plan(
    risks: list[dict[str, Any]],
    incoming: dict[str, dict[int, int]],
    selected_offers: list[dict[str, Any]],
    solution: dict[str, Any],
) -> dict[str, list[dict[str, int]]]:
    purchased: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for item in selected_offers:
        offer = item["offer"]
        purchased[offer["ingredient_id"]][item["arrivalDay"]] += item["packs"] * offer["pack_quantity_base"]
    plan = {}
    for risk in risks:
        ingredient_id = risk["ingredientId"]
        rows = []
        for day in range(1, HORIZON_DAYS + 1):
            required = int(risk["_base"]["dailyRequired"][day - 1])
            shortage = solution["shortages"][ingredient_id][day - 1]
            rows.append(
                {
                    "day": day,
                    "requiredBase": required,
                    "incomingBase": int(incoming.get(ingredient_id, {}).get(day, 0)),
                    "purchasedArrivalBase": purchased[ingredient_id][day],
                    "servedBase": required - shortage,
                    "shortageBase": shortage,
                    "endingInventoryBase": solution["inventories"][ingredient_id][day - 1],
                }
            )
        plan[ingredient_id] = rows
    return plan


def _timing_limitations(
    risks: list[dict[str, Any]],
    arrival_days: dict[str, int],
    by_ingredient: dict[str, list[dict[str, Any]]],
    solution: dict[str, Any],
) -> list[str]:
    """Flag shortages that no eligible offer can reach because they occur before its earliest arrival."""
    limitations = []
    for risk in risks:
        ingredient_id = risk["ingredientId"]
        eligible = [arrival_days[o["id"]] for o in by_ingredient.get(ingredient_id, []) if o["id"] in arrival_days]
        earliest = min(eligible) if eligible else HORIZON_DAYS + 1
        early = sum(solution["shortages"][ingredient_id][: earliest - 1])
        if early:
            limitations.append(f"SHORTAGE_BEFORE_EARLIEST_ARRIVAL:{ingredient_id}:{early}")
    return limitations
