from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

import psycopg

from app.core.config import Settings
from app.inventory.db import balances_base, from_base, now_utc
from app.inventory.forecast import ensure_forecast, validation_mae_by_horizon

HORIZON_DAYS = 3


def project_daily(*, current_base: int, daily_required: list[int]) -> dict[str, Any]:
    """Project stock without replenishment and record the per-day unmet requirement."""
    running = current_base
    projected = []
    shortfall = []
    first_stockout_day = None
    for day, required in enumerate(daily_required, start=1):
        shortfall.append(max(0, required - max(0, running)))
        running -= required
        projected.append(running)
        if running < 0 and first_stockout_day is None:
            first_stockout_day = day
    return {
        "projected": projected,
        "ending": running,
        "dailyShortfall": shortfall,
        "firstStockoutDay": first_stockout_day,
    }


def priority_key(item: dict[str, Any]) -> tuple:
    """Deterministic urgency order; smaller keys are more urgent.

    Inputs: first stockout day, lost-sales value of the unreplenished shortfall, shortfall share of
    requirement, D+1 requirement value, and validation-derived forecast uncertainty value.
    """
    base = item["_base"]
    value = float(base["lostSalesIdrPerBase"])
    shortfall = sum(base["dailyShortfall"])
    required = base["required"]
    return (
        base["firstStockoutDay"] or HORIZON_DAYS + 1,
        -shortfall * value,
        -(shortfall / required if required else 0.0),
        -base["dailyRequired"][0] * value,
        -base["forecastUncertaintyBase"] * value,
        item["ingredientId"],
    )


def assign_priorities(items: list[dict[str, Any]]) -> None:
    for rank, item in enumerate(sorted(items, key=priority_key), start=1):
        item["_base"]["priorityRank"] = rank


def classify_risk(
    *,
    current_base: int,
    total_required_base: int,
    ending_base: int,
    safety_stock_base: int,
    projected_stockout_date: Any,
) -> tuple[str, str, list[str]]:
    if current_base == 0 and total_required_base > 0:
        return "STOCKOUT", "Stok tersedia nol sementara kebutuhan forecast positif.", ["NO_USABLE_STOCK"]
    if projected_stockout_date is not None:
        return "HIGH", "Stok diproyeksikan menjadi negatif dalam horizon tiga hari.", ["PROJECTED_NEGATIVE_STOCK"]
    if ending_base < safety_stock_base:
        return "MEDIUM", "Stok akhir diproyeksikan berada di bawah safety stock.", ["BELOW_SAFETY_STOCK"]
    return "LOW", "Stok diproyeksikan mencukupi kebutuhan dan safety stock.", ["COVERED_WITH_SAFETY_STOCK"]


def evaluate_risks(
    connection: psycopg.Connection,
    settings: Settings,
    *,
    correlation_id: str,
) -> dict[str, Any]:
    run = ensure_forecast(connection, settings, correlation_id=correlation_id)
    requirements: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    revenue: dict[str, int] = defaultdict(int)
    rows = connection.execute(
        "SELECT f.horizon,r.ingredient_id,sum(f.predicted_demand*r.quantity_required_base)::bigint AS required_base,"
        "sum(f.predicted_demand*p.price_idr)::bigint AS revenue_idr "
        "FROM inventory_forecast_item f JOIN inventory_recipe r ON r.product_id=f.product_id "
        "JOIN inventory_product p ON p.id=f.product_id "
        "WHERE f.run_id=%s GROUP BY f.horizon,r.ingredient_id",
        (run["id"],),
    ).fetchall()
    for row in rows:
        requirements[row["ingredient_id"]][row["horizon"]] = row["required_base"]
        revenue[row["ingredient_id"]] += row["revenue_idr"]
    recipe_totals = {
        row["ingredient_id"]: row["recipe_base"]
        for row in connection.execute(
            "SELECT r.ingredient_id,sum(r.quantity_required_base)::bigint AS recipe_base FROM inventory_recipe r "
            "JOIN inventory_product p ON p.id=r.product_id WHERE p.active GROUP BY r.ingredient_id"
        ).fetchall()
    }
    horizon_mae = validation_mae_by_horizon(settings, fallback=run["source"] == "FALLBACK")

    ingredients = connection.execute(
        "SELECT i.*,COALESCE(min(s.lead_time_hours),0)::integer AS lead_time_hours "
        "FROM inventory_ingredient i "
        "LEFT JOIN inventory_supplier_offer o ON o.ingredient_id=i.id AND o.active "
        "LEFT JOIN inventory_supplier s ON s.id=o.supplier_id AND s.active "
        "WHERE i.active GROUP BY i.id ORDER BY i.id"
    ).fetchall()
    balances = balances_base(connection)
    state = connection.execute("SELECT inventory_version FROM inventory_state WHERE id=1").fetchone()
    items: list[dict[str, Any]] = []
    for ingredient in ingredients:
        current_base = balances.get(ingredient["id"], 0)
        daily_required = [requirements[ingredient["id"]].get(horizon, 0) for horizon in range(1, HORIZON_DAYS + 1)]
        total_required_base = sum(daily_required)
        projection = project_daily(current_base=current_base, daily_required=daily_required)
        running_base = projection["ending"]
        stockout_date = (
            run["as_of_date"] + timedelta(days=projection["firstStockoutDay"])
            if projection["firstStockoutDay"]
            else None
        )
        projections = [
            {
                "date": run["as_of_date"] + timedelta(days=horizon),
                "requirement": from_base(required_base, ingredient),
                "incomingQuantity": 0.0,
                "projectedStock": from_base(projected_base, ingredient),
            }
            for horizon, required_base, projected_base in zip(
                range(1, HORIZON_DAYS + 1), daily_required, projection["projected"], strict=True
            )
        ]

        level, reason, reason_codes = classify_risk(
            current_base=current_base,
            total_required_base=total_required_base,
            ending_base=running_base,
            safety_stock_base=ingredient["safety_stock_base"],
            projected_stockout_date=stockout_date,
        )
        if ingredient["lead_time_hours"] > 72:
            reason_codes.append("LEAD_TIME_EXCEEDS_HORIZON")
        items.append(
            {
                "ingredientId": ingredient["id"],
                "ingredientName": ingredient["name"],
                "unit": ingredient["api_unit"],
                "currentStock": from_base(current_base, ingredient),
                "incomingStock": 0.0,
                "predictedRequirement": from_base(total_required_base, ingredient),
                "projectedStock": from_base(running_base, ingredient),
                "safetyStock": from_base(ingredient["safety_stock_base"], ingredient),
                "reorderPoint": from_base(ingredient["reorder_point_base"], ingredient),
                "leadTimeHours": ingredient["lead_time_hours"],
                "riskLevel": level,
                "riskReason": reason,
                "reasonCodes": reason_codes,
                "projectedStockoutDate": stockout_date,
                "inventoryVersion": str(state["inventory_version"]),
                "forecastRunId": str(run["id"]),
                "dailyProjection": projections,
                "_base": {
                    "current": current_base,
                    "required": total_required_base,
                    "projected": running_base,
                    "safety": ingredient["safety_stock_base"],
                    "storageCapacity": ingredient["storage_capacity_base"],
                    "dailyRequired": daily_required,
                    "dailyShortfall": projection["dailyShortfall"],
                    "firstStockoutDay": projection["firstStockoutDay"],
                    "lostSalesIdrPerBase": revenue[ingredient["id"]] / total_required_base
                    if total_required_base
                    else 0.0,
                    "forecastUncertaintyBase": round(sum(horizon_mae) * recipe_totals.get(ingredient["id"], 0)),
                },
            }
        )
    assign_priorities(items)
    return {
        "generatedAt": now_utc(),
        "horizonDays": 3,
        "forecastRun": run,
        "items": items,
    }


def inventory_view(
    connection: psycopg.Connection,
    settings: Settings,
    *,
    correlation_id: str,
    search: str | None,
    risk_level: str | None,
) -> dict[str, Any]:
    risks = evaluate_risks(connection, settings, correlation_id=correlation_id)
    needle = search.casefold().strip() if search else None
    items = []
    for risk in risks["items"]:
        if risk_level and risk["riskLevel"] != risk_level:
            continue
        if needle and needle not in risk["ingredientName"].casefold() and needle not in risk["ingredientId"].casefold():
            continue
        items.append(
            {
                "ingredientId": risk["ingredientId"],
                "ingredientName": risk["ingredientName"],
                "category": "Buah",
                "currentStock": risk["currentStock"],
                "unit": risk["unit"],
                "predictedRequirement": risk["predictedRequirement"],
                "requirementHorizonDays": 3,
                "riskLevel": risk["riskLevel"],
                "riskReason": risk["riskReason"],
                "updatedAt": risks["generatedAt"],
            }
        )
    return {"items": items}


def public_risks(result: dict[str, Any], level: str | None = None) -> dict[str, Any]:
    items = []
    for item in result["items"]:
        if level and item["riskLevel"] != level:
            continue
        items.append({key: value for key, value in item.items() if key != "_base"})
    return {"generatedAt": result["generatedAt"], "horizonDays": 3, "items": items}
