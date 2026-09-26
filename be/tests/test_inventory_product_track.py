from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from ortools.sat.python import cp_model
from pydantic import ValidationError

from app.core.config import Settings
from app.errors import ApiError
from app.inventory.db import WIB, business_date, from_base, to_base
from app.inventory.explanation import apply_qwen_explanations
from app.inventory.optimization import map_solver_status, optimize_procurement
from app.inventory.procurement import arrival_day
from app.inventory.risk import assign_priorities, classify_risk, project_daily
from app.inventory.schemas import CreateTransactionRequest, QwenExplanationOutput
from app.main import create_app


def test_wib_business_date_boundary_is_independent_of_server_timezone() -> None:
    assert business_date(datetime(2026, 9, 30, 16, 59, tzinfo=UTC)).isoformat() == "2026-09-30"
    assert business_date(datetime(2026, 9, 30, 17, 0, tzinfo=UTC)).isoformat() == "2026-10-01"
    assert WIB.key == "Asia/Jakarta"


def test_quantity_conversion_preserves_precision_and_discrete_units() -> None:
    weight = {"storage_scale": 1_000_000, "quantity_kind": "weight", "api_unit": "kg"}
    pieces = {"storage_scale": 1, "quantity_kind": "discrete", "api_unit": "pcs"}
    assert to_base(0.25, weight) == 250_000
    assert from_base(250_000, weight) == 0.25
    assert to_base(3, pieces) == 3
    with pytest.raises(ApiError) as raised:
        to_base(1.5, pieces)
    assert raised.value.code == "UNSUPPORTED_PRECISION"


def test_transaction_quantity_is_a_positive_integer() -> None:
    with pytest.raises(ValidationError):
        CreateTransactionRequest.model_validate(
            {"source": "POS_SIMULATOR", "items": [{"productId": "P001", "quantity": 1.5}]}
        )


@pytest.mark.parametrize(
    ("current", "required", "ending", "safety", "stockout", "expected"),
    [
        (0, 1, -1, 0, "2026-09-27", "STOCKOUT"),
        (10, 15, -5, 2, "2026-09-28", "HIGH"),
        (10, 8, 2, 3, None, "MEDIUM"),
        (10, 0, 10, 3, None, "LOW"),
        (0, 0, 0, 0, None, "LOW"),
    ],
)
def test_risk_precedence(current, required, ending, safety, stockout, expected) -> None:
    level, _, _ = classify_risk(
        current_base=current,
        total_required_base=required,
        ending_base=ending,
        safety_stock_base=safety,
        projected_stockout_date=stockout,
    )
    assert level == expected


def test_inventory_routes_use_canonical_error_envelope_without_database() -> None:
    settings = Settings(app_env="test", inventory_database_url=None)
    with TestClient(create_app(settings)) as client:
        validation = client.post("/api/transactions", json={"source": "POS_SIMULATOR", "items": []})
        unavailable = client.get("/api/products")
    assert validation.status_code == 422
    assert validation.json()["error"]["code"] == "VALIDATION_ERROR"
    assert unavailable.status_code == 503
    assert unavailable.json() == {
        "error": {
            "code": "INVENTORY_UNCONFIGURED",
            "message": "INVENTORY_DATABASE_URL belum diatur.",
            "details": None,
        }
    }


def test_required_frontend_endpoint_matrix_is_registered() -> None:
    paths = set(create_app(Settings(app_env="test", inventory_database_url=None)).openapi()["paths"])
    assert {
        "/api/products",
        "/api/transactions",
        "/api/transactions/{transaction_id}",
        "/api/inventory",
        "/api/inventory/movements",
        "/api/inventory/{ingredient_id}/adjustments",
        "/api/inventory/{ingredient_id}/stock-in",
        "/api/forecasts/products/{product_id}",
        "/api/inventory/risks",
        "/api/procurement/recommendations",
        "/api/procurement/recommendations/{recommendation_id}/decision",
        "/api/dashboard/summary",
    }.issubset(paths)


def test_forecast_artifact_records_temporal_split_and_baselines() -> None:
    manifest_path = Path(__file__).resolve().parents[1] / "artifacts" / "inventory" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["syntheticData"] is True
    assert manifest["excludedSplits"] == ["embargo", "inference_only", "warmup"]
    assert manifest["splitDates"]["train"]["max"] < manifest["splitDates"]["validation"]["min"]
    assert manifest["splitDates"]["validation"]["max"] < manifest["splitDates"]["test"]["min"]
    assert all(
        values[split]["xgboostMae"] < values[split]["persistenceMae"]
        for values in manifest["metrics"].values()
        for split in ("validation", "test")
    )


def test_qwen_structured_output_rejects_missing_fields() -> None:
    with pytest.raises(ValidationError):
        QwenExplanationOutput.model_validate({"summary": "ok"})


def test_qwen_offline_uses_deterministic_fallback_without_writes() -> None:
    class NoWriteConnection:
        def execute(self, *_args, **_kwargs):
            raise AssertionError("fallback must not update recommendation values")

    plan = {
        "planId": "plan-1",
        "inventoryVersion": "1",
        "forecastRunId": "forecast-1",
        "optimizerStatus": "OPTIMAL",
        "planOutcome": "COMPLETE",
        "totalEstimatedCost": 100_000,
        "limitations": [],
        "recommendations": [
            {
                "id": "recommendation-1",
                "ingredientId": "ING-001",
                "ingredientName": "Jeruk",
                "unit": "kg",
                "currentStock": 2.0,
                "predictedRequirement": 5.0,
                "safetyStock": 3.0,
                "projectedStock": -3.0,
                "riskLevel": "HIGH",
                "recommendedOrderQuantity": 5.0,
                "supplier": {"id": "SUP-001", "name": "Demo", "leadTimeHours": 24},
                "expectedArrivalAt": "2026-09-27T05:00:00Z",
                "estimatedCost": 100_000,
                "unmetQuantity": 0.0,
                "reasonCodes": ["PROJECTED_SHORTAGE"],
            }
        ],
    }
    settings = Settings(app_env="test", explanation_mode="deterministic", openrouter_api_key=None)

    assert apply_qwen_explanations(NoWriteConnection(), settings, plan) == "FALLBACK"


def _risk(ingredient_id, *, current, daily, safety=0, storage=None, value=1.0, rank=1):
    return {
        "ingredientId": ingredient_id,
        "riskLevel": "HIGH",
        "_base": {
            "current": current,
            "required": sum(daily),
            "safety": safety,
            "storageCapacity": storage,
            "dailyRequired": daily,
            "lostSalesIdrPerBase": value,
            "priorityRank": rank,
        },
    }


def _offer(offer_id, ingredient_id, *, lead, pack, cost, moq=1, capacity=10):
    return {
        "id": offer_id,
        "ingredient_id": ingredient_id,
        "lead_time_hours": lead,
        "pack_quantity_base": pack,
        "pack_cost_idr": cost,
        "minimum_packs": moq,
        "capacity_packs": capacity,
    }


def _packs(result):
    return {item["offer"]["id"]: item["packs"] for item in result["selectedOffers"]}


def test_optimizer_credits_supply_only_from_its_arrival_day() -> None:
    # One affordable pack arriving on day 2: it cannot rescue day-1 demand, so it must go to B.
    result = optimize_procurement(
        risks=[_risk("A", current=0, daily=[10, 0, 0]), _risk("B", current=0, daily=[0, 0, 10], rank=2)],
        offers=[_offer("oa", "A", lead=48, pack=10, cost=100), _offer("ob", "B", lead=48, pack=10, cost=100)],
        budget_idr=100,
    )
    assert result["optimizerStatus"] == "OPTIMAL"
    assert _packs(result) == {"ob": 1}
    assert result["unmet"] == {"A": 10, "B": 0}
    assert "SHORTAGE_BEFORE_EARLIEST_ARRIVAL:A:10" in result["limitations"]
    assert result["planOutcome"] == "PARTIAL"


def test_optimizer_prefers_cheaper_offer_when_service_is_equal() -> None:
    result = optimize_procurement(
        risks=[_risk("A", current=0, daily=[0, 10, 0])],
        offers=[_offer("fast", "A", lead=24, pack=10, cost=150), _offer("slow", "A", lead=48, pack=10, cost=100)],
        budget_idr=1_000,
    )
    assert _packs(result) == {"slow": 1}
    assert result["planOutcome"] == "COMPLETE"
    assert [stage["status"] for stage in result["objectiveStages"]] == ["OPTIMAL"] * 4


def test_optimizer_storage_ignores_forecast_consumption() -> None:
    # Day-1 consumption would free room, but storage must hold even if that demand never happens.
    result = optimize_procurement(
        risks=[_risk("A", current=8, daily=[8, 8, 0], storage=10)],
        offers=[_offer("oa", "A", lead=48, pack=1, cost=1, capacity=20)],
        budget_idr=1_000,
    )
    assert _packs(result) == {"oa": 2}
    assert result["unmet"] == {"A": 6}


def test_optimizer_fills_safety_stock_before_minimizing_cost_and_respects_moq() -> None:
    result = optimize_procurement(
        risks=[_risk("A", current=0, daily=[5, 0, 0], safety=5)],
        offers=[_offer("oa", "A", lead=0, pack=1, cost=10, moq=3, capacity=20)],
        budget_idr=10_000,
    )
    assert _packs(result) == {"oa": 10}
    assert result["unmet"] == {"A": 0}
    assert result["totalEstimatedCost"] == 100


def test_optimizer_daily_plan_balances_with_non_divisible_quantities() -> None:
    risks = [_risk("A", current=7, daily=[3, 5, 11], safety=2, storage=40)]
    offers = [_offer("oa", "A", lead=24, pack=13, cost=7, capacity=3)]
    first = optimize_procurement(risks=risks, offers=offers, budget_idr=100)
    second = optimize_procurement(risks=risks, offers=offers, budget_idr=100)
    assert first["optimizerStatus"] == "OPTIMAL"
    assert first["selectedOffers"] == second["selectedOffers"]
    stock = 7
    for row in first["dailyPlan"]["A"]:
        assert row["servedBase"] + row["shortageBase"] == row["requiredBase"]
        stock += row["incomingBase"] + row["purchasedArrivalBase"] - row["servedBase"]
        assert stock == row["endingInventoryBase"] >= 0


def test_optimizer_respects_shared_budget_and_reserved_cost() -> None:
    result = optimize_procurement(
        risks=[_risk("A", current=0, daily=[0, 10, 10]), _risk("B", current=0, daily=[0, 10, 10], rank=2)],
        offers=[_offer("oa", "A", lead=24, pack=10, cost=100), _offer("ob", "B", lead=24, pack=10, cost=100)],
        budget_idr=400,
        reserved_cost_idr=100,
    )
    assert result["availableBudget"] == 300
    assert result["totalEstimatedCost"] <= 300
    assert sum(_packs(result).values()) == 3


def test_project_daily_records_first_stockout_and_daily_shortfall() -> None:
    projection = project_daily(current_base=5, daily_required=[3, 3, 3])
    assert projection == {
        "projected": [2, -1, -4],
        "ending": -4,
        "dailyShortfall": [0, 1, 3],
        "firstStockoutDay": 2,
    }


def test_priority_ranks_earliest_stockout_then_lost_sales_value() -> None:
    def item(ingredient_id, stockout_day, shortfall, value):
        return {
            "ingredientId": ingredient_id,
            "_base": {
                "firstStockoutDay": stockout_day,
                "dailyShortfall": [0, 0, shortfall],
                "dailyRequired": [5, 5, 5],
                "required": 15,
                "lostSalesIdrPerBase": value,
                "forecastUncertaintyBase": 3,
            },
        }

    items = [
        item("late-high", 2, 9, 5.0),
        item("safe", None, 0, 9.0),
        item("early", 1, 1, 1.0),
        item("late-low", 2, 9, 1.0),
    ]
    assign_priorities(items)
    assert {entry["ingredientId"]: entry["_base"]["priorityRank"] for entry in items} == {
        "early": 1,
        "late-high": 2,
        "late-low": 3,
        "safe": 4,
    }


def test_arrival_day_uses_wib_business_date_of_expected_arrival() -> None:
    ordered_at = datetime(2026, 9, 27, 3, 0, tzinfo=UTC)  # 10:00 WIB on the first forecast day
    as_of = datetime(2026, 9, 26).date()
    assert arrival_day(ordered_at, 0, as_of) == 1
    assert arrival_day(ordered_at, 24, as_of) == 2
    assert arrival_day(ordered_at, 72, as_of) == 4


def test_procurement_maps_infeasible_and_timeout_status_truthfully() -> None:
    model = cp_model.CpModel()
    value = model.new_int_var(0, 1, "value")
    model.add(value == 0)
    model.add(value == 1)

    assert map_solver_status(cp_model.CpSolver().solve(model)) == "INFEASIBLE"
    assert map_solver_status(cp_model.UNKNOWN) == "ERROR"
