from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "be"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings
from app.inventory.forecast import predict_products, validation_mae_by_horizon
from app.inventory.optimization import optimize_procurement
from app.inventory.risk import assign_priorities, classify_risk, project_daily

BASE_PER_KG = 1_000_000


def load_dataset(specification: dict[str, Any]) -> pd.DataFrame:
    path = REPO_ROOT / specification["path"]
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != specification["sha256"]:
        raise RuntimeError("Inventory evaluation dataset hash mismatch")
    frame = pd.read_csv(path)
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    return frame


def _history(
    frame: pd.DataFrame, product_ids: list[str], as_of: date
) -> dict[str, dict[date, int]]:
    subset = frame[
        (frame["date"] <= as_of) & (frame["date"] >= as_of - timedelta(days=60))
    ]
    histories: dict[str, dict[date, int]] = {}
    for product_id in product_ids:
        rows = subset[subset["product_id"] == product_id]
        histories[product_id] = {
            row.date: int(row.demand_cups_t) for row in rows.itertuples(index=False)
        }
    return histories


def _actual(
    frame: pd.DataFrame, product_ids: list[str], as_of: date
) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for product_id in product_ids:
        indexed = frame[frame["product_id"] == product_id].set_index("date")[
            "demand_cups_t"
        ]
        result[product_id] = [
            int(indexed.loc[as_of + timedelta(days=horizon)]) for horizon in (1, 2, 3)
        ]
    return result


def run_system(
    case: dict[str, Any], defaults: dict[str, Any], frame: pd.DataFrame
) -> dict[str, Any]:
    as_of = date.fromisoformat(case["asOfDate"])
    product_ids = sorted(frame["product_id"].unique().tolist())
    ingredient_by_product = {
        product_id: f"ING-{product_id[1:]}" for product_id in product_ids
    }
    settings = Settings(
        app_env="test", inventory_model_dir=BACKEND_DIR / "artifacts" / "inventory"
    )
    manifest, predictions = predict_products(
        settings,
        product_ids=product_ids,
        histories=_history(frame, product_ids, as_of),
        as_of=as_of,
    )

    initial_kg = float(case.get("initialStockKg", defaults["initialStockKg"]))
    safety_kg = float(case.get("safetyStockKg", defaults["safetyStockKg"]))
    capacity_kg = float(case.get("storageCapacityKg", defaults["storageCapacityKg"]))
    recipe_kg = float(defaults["recipeKgPerCup"])
    recipe_base = round(recipe_kg * BASE_PER_KG)
    horizon_mae = validation_mae_by_horizon(settings)
    risks = []
    for product_id in product_ids:
        ingredient_id = ingredient_by_product[product_id]
        daily_required = [value * recipe_base for value in predictions[product_id]]
        current = round(initial_kg * BASE_PER_KG)
        projection = project_daily(current_base=current, daily_required=daily_required)
        stockout_date = (
            as_of + timedelta(days=projection["firstStockoutDay"])
            if projection["firstStockoutDay"]
            else None
        )
        required = sum(daily_required)
        safety = round(safety_kg * BASE_PER_KG)
        level, reason, reason_codes = classify_risk(
            current_base=current,
            total_required_base=required,
            ending_base=projection["ending"],
            safety_stock_base=safety,
            projected_stockout_date=stockout_date,
        )
        risks.append(
            {
                "ingredientId": ingredient_id,
                "riskLevel": level,
                "riskReason": reason,
                "reasonCodes": reason_codes,
                "projectedStockoutDate": stockout_date.isoformat()
                if stockout_date
                else None,
                "_base": {
                    "current": current,
                    "required": required,
                    "safety": safety,
                    "storageCapacity": round(capacity_kg * BASE_PER_KG),
                    "dailyRequired": daily_required,
                    "dailyShortfall": projection["dailyShortfall"],
                    "firstStockoutDay": projection["firstStockoutDay"],
                    "lostSalesIdrPerBase": int(defaults["salePriceIdr"]) / recipe_base,
                    "forecastUncertaintyBase": round(sum(horizon_mae) * recipe_base),
                },
            }
        )
    assign_priorities(risks)

    offer_templates = case.get("offers", defaults["offers"])
    offers = []
    for product_id in product_ids:
        ingredient_id = ingredient_by_product[product_id]
        for template in offer_templates:
            offers.append(
                {
                    "id": f"{template['id']}:{ingredient_id}",
                    "template_id": template["id"],
                    "ingredient_id": ingredient_id,
                    "supplier_id": template["supplierId"],
                    "supplier_name": template["supplierName"],
                    "lead_time_hours": int(template["leadTimeHours"]),
                    "pack_quantity_base": round(
                        float(template["packQuantityKg"]) * BASE_PER_KG
                    ),
                    "minimum_packs": int(template["minimumPacks"]),
                    "capacity_packs": int(template["capacityPacks"]),
                    "pack_cost_idr": int(template["packCostIdr"]),
                }
            )
    optimization = optimize_procurement(
        risks=risks,
        offers=offers,
        budget_idr=int(case.get("budgetIdr", defaults["budgetIdr"])),
        timeout_seconds=5.0,
    )
    decisions = []
    for selected in optimization["selectedOffers"]:
        offer = selected["offer"]
        packs = selected["packs"]
        decisions.append(
            {
                "ingredientId": offer["ingredient_id"],
                "offerId": offer["template_id"],
                "supplierId": offer["supplier_id"],
                "packCount": packs,
                "packQuantityBase": offer["pack_quantity_base"],
                "quantityBase": packs * offer["pack_quantity_base"],
                "minimumPacks": offer["minimum_packs"],
                "capacityPacks": offer["capacity_packs"],
                "packCostIdr": offer["pack_cost_idr"],
                "totalCostIdr": packs * offer["pack_cost_idr"],
                "leadTimeHours": offer["lead_time_hours"],
            }
        )
    return {
        "modelVersion": manifest["version"],
        "asOfDate": as_of.isoformat(),
        "productIds": product_ids,
        "ingredientByProduct": ingredient_by_product,
        "predictions": predictions,
        "actualDemand": _actual(frame, product_ids, as_of),
        "risks": risks,
        "offers": offers,
        "optimizerVersion": optimization["optimizerVersion"],
        "objectiveStages": optimization["objectiveStages"],
        "optimizerStatus": optimization["optimizerStatus"],
        "planOutcome": optimization["planOutcome"],
        "solverStatusDetail": optimization["solverStatusDetail"],
        "limitations": optimization["limitations"],
        "totalEstimatedCostIdr": optimization["totalEstimatedCost"],
        "decisions": decisions,
        "input": {
            "initialStockBase": round(initial_kg * BASE_PER_KG),
            "storageCapacityBase": round(capacity_kg * BASE_PER_KG),
            "recipeBasePerCup": recipe_base,
            "budgetIdr": int(case.get("budgetIdr", defaults["budgetIdr"])),
            "salePriceIdr": int(defaults["salePriceIdr"]),
            "stockoutCostIdrPerCup": int(defaults["stockoutCostIdrPerCup"]),
            "holdingCostIdrPerKgDay": int(defaults["holdingCostIdrPerKgDay"]),
        },
    }


def canonical_decision_hash(system_output: dict[str, Any]) -> str:
    canonical = json.dumps(
        system_output["decisions"], sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
