from __future__ import annotations

from typing import Any

import psycopg

from app.core.config import Settings
from app.inventory.db import WIB, now_utc
from app.inventory.procurement import recommendations
from app.inventory.risk import evaluate_risks


def summary(
    connection: psycopg.Connection,
    settings: Settings,
    *,
    correlation_id: str,
) -> dict[str, Any]:
    today = now_utc().astimezone(WIB).date()
    sales = connection.execute(
        "SELECT COALESCE(sum(total_amount_idr),0)::bigint AS revenue,count(*)::integer AS transactions,"
        "COALESCE(sum(total_items),0)::integer AS products_sold FROM inventory_sale "
        "WHERE status='COMPLETED' AND business_date=%s",
        (today,),
    ).fetchone()
    risks = evaluate_risks(connection, settings, correlation_id=correlation_id)
    plan = recommendations(connection, settings, correlation_id=correlation_id)
    active = [item for item in plan["recommendations"] if item["status"] == "PENDING"]
    priority = [
        {
            "recommendationId": item["id"],
            "ingredientId": item["ingredientId"],
            "ingredientName": item["ingredientName"],
            "riskLevel": item["riskLevel"],
            "recommendedOrderQuantity": item["recommendedOrderQuantity"],
            "unit": item["unit"],
            "recommendedOrderAt": item["recommendedOrderAt"],
            "summary": item["explanation"]["text"],
        }
        for item in active
    ]
    return {
        "generatedAt": now_utc(),
        "today": {
            "revenue": sales["revenue"],
            "currency": "IDR",
            "transactions": sales["transactions"],
            "productsSold": sales["products_sold"],
        },
        "inventory": {
            "atRiskIngredientCount": sum(
                item["riskLevel"] in {"MEDIUM", "HIGH", "STOCKOUT"} for item in risks["items"]
            ),
            "activeRecommendationCount": len(active),
        },
        "priorityActions": priority,
    }
