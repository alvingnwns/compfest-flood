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
from app.inventory.optimization import map_solver_status
from app.inventory.risk import classify_risk
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
    paths = {route.path for route in create_app(Settings(app_env="test", inventory_database_url=None)).routes}
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


def test_procurement_maps_infeasible_and_timeout_status_truthfully() -> None:
    model = cp_model.CpModel()
    value = model.new_int_var(0, 1, "value")
    model.add(value == 0)
    model.add(value == 1)

    assert map_solver_status(cp_model.CpSolver().solve(model)) == "INFEASIBLE"
    assert map_solver_status(cp_model.UNKNOWN) == "ERROR"
