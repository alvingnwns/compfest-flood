from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

import psycopg

from app.core.config import Settings
from app.inventory.db import balances_base, from_base, now_utc
from app.inventory.forecast import ensure_forecast


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
    rows = connection.execute(
        "SELECT f.horizon,r.ingredient_id,sum(f.predicted_demand*r.quantity_required_base)::bigint AS required_base "
        "FROM inventory_forecast_item f JOIN inventory_recipe r ON r.product_id=f.product_id "
        "WHERE f.run_id=%s GROUP BY f.horizon,r.ingredient_id",
        (run["id"],),
    ).fetchall()
    for row in rows:
        requirements[row["ingredient_id"]][row["horizon"]] = row["required_base"]

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
        running_base = current_base
        total_required_base = 0
        stockout_date = None
        projections = []
        for horizon in (1, 2, 3):
            required_base = requirements[ingredient["id"]].get(horizon, 0)
            total_required_base += required_base
            running_base -= required_base
            forecast_date = run["as_of_date"] + timedelta(days=horizon)
            if running_base < 0 and stockout_date is None:
                stockout_date = forecast_date
            projections.append(
                {
                    "date": forecast_date,
                    "requirement": from_base(required_base, ingredient),
                    "incomingQuantity": 0.0,
                    "projectedStock": from_base(running_base, ingredient),
                }
            )

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
                },
            }
        )
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
