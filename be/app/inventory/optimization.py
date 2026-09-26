from __future__ import annotations

from collections import defaultdict
from typing import Any

from ortools.sat.python import cp_model

from app.errors import ApiError

RISK_PENALTY = {"STOCKOUT": 10_000, "HIGH": 1_000, "MEDIUM": 100, "LOW": 10}


def map_solver_status(status: cp_model.CpSolverStatus) -> str:
    if status == cp_model.OPTIMAL:
        return "OPTIMAL"
    if status == cp_model.FEASIBLE:
        return "FEASIBLE"
    if status == cp_model.INFEASIBLE:
        return "INFEASIBLE"
    return "ERROR"


def optimize_procurement(
    *,
    risks: list[dict[str, Any]],
    offers: list[dict[str, Any]],
    budget_idr: int,
    reserved_cost_idr: int = 0,
    approved_outstanding: dict[str, int] | None = None,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    """Run the production CP-SAT decision model without persistence concerns."""
    outstanding = approved_outstanding or {}
    available_budget = max(0, budget_idr - reserved_cost_idr)
    by_ingredient: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for offer in offers:
        by_ingredient[offer["ingredient_id"]].append(offer)

    model = cp_model.CpModel()
    pack_vars: dict[str, Any] = {}
    shortage_vars: dict[str, Any] = {}
    targets: dict[str, int] = {}
    limitations: list[str] = []
    total_cost_terms = []
    objective_terms = []
    for risk in risks:
        ingredient_id = risk["ingredientId"]
        base = risk["_base"]
        coverage_gap = max(0, base["required"] + base["safety"] - base["current"])
        reserved_quantity = outstanding.get(ingredient_id, 0)
        target = max(0, coverage_gap - reserved_quantity)
        if reserved_quantity:
            limitations.append(f"APPROVED_QUANTITY_UNCONFIRMED:{ingredient_id}:{reserved_quantity}")
        targets[ingredient_id] = target
        relevant = [offer for offer in by_ingredient.get(ingredient_id, []) if offer["lead_time_hours"] <= 72]
        if not relevant and target > 0:
            limitations.append(f"NO_ELIGIBLE_SUPPLIER_WITHIN_HORIZON:{ingredient_id}")
        purchase_terms = []
        for offer in relevant:
            capacity_packs = offer["capacity_packs"]
            if capacity_packs is None:
                raise ApiError(
                    422,
                    "MISSING_PROCUREMENT_CONSTRAINT",
                    "Supplier capacity harus dikonfigurasi untuk optimizer.",
                    details={"offerId": offer["id"], "field": "capacity"},
                )
            packs = model.new_int_var(0, capacity_packs, f"packs_{offer['id']}")
            selected = model.new_bool_var(f"selected_{offer['id']}")
            model.add(packs == 0).only_enforce_if(selected.Not())
            model.add(packs >= offer["minimum_packs"]).only_enforce_if(selected)
            model.add(packs <= capacity_packs).only_enforce_if(selected)
            pack_vars[offer["id"]] = packs
            purchase_terms.append(packs * offer["pack_quantity_base"])
            total_cost_terms.append(packs * offer["pack_cost_idr"])
        shortage = model.new_int_var(0, target, f"shortage_{ingredient_id}")
        shortage_vars[ingredient_id] = shortage
        purchased = sum(purchase_terms) if purchase_terms else 0
        model.add(shortage >= target - purchased)
        if base["storageCapacity"] is not None and purchase_terms:
            available_storage = max(0, base["storageCapacity"] - base["current"])
            model.add(purchased <= available_storage)
        objective_terms.append(shortage * RISK_PENALTY[risk["riskLevel"]])
    if total_cost_terms:
        model.add(sum(total_cost_terms) <= available_budget)
        objective_terms.extend(total_cost_terms)
    model.minimize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    solver.parameters.num_search_workers = 1
    status = solver.solve(model)
    status_name = solver.status_name(status)
    optimizer_status = map_solver_status(status)

    selected_offers: list[dict[str, Any]] = []
    if status in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        for offer in offers:
            variable = pack_vars.get(offer["id"])
            if variable is not None and (packs := solver.value(variable)) > 0:
                selected_offers.append({"offer": offer, "packs": packs})
        unmet = {ingredient_id: solver.value(variable) for ingredient_id, variable in shortage_vars.items()}
        plan_outcome = "COMPLETE" if not any(unmet.values()) else "PARTIAL"
    else:
        unmet = targets
        plan_outcome = "INFEASIBLE"

    total_cost = sum(item["offer"]["pack_cost_idr"] * item["packs"] for item in selected_offers)
    return {
        "optimizerStatus": optimizer_status,
        "solverStatusDetail": status_name,
        "planOutcome": plan_outcome,
        "selectedOffers": selected_offers,
        "unmet": unmet,
        "targets": targets,
        "limitations": limitations,
        "totalEstimatedCost": total_cost,
        "availableBudget": available_budget,
    }
