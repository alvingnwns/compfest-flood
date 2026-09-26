"""Real PostgreSQL regression tests: NEVER use the shared/demo database."""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict
from pydantic import SecretStr

from app.core.config import Settings
from app.errors import ApiError
from app.inventory.db import balances_base, connect
from app.inventory.operations import create_transaction
from app.inventory.schemas import CreateTransactionRequest
from app.inventory.operations import get_transaction, list_movements, stock_in
from app.inventory.forecast import product_forecast
from app.inventory.procurement import decide, recommendations
from app.inventory.risk import evaluate_risks
from app.inventory.schemas import ProcurementResponse, StockInRequest
from uuid import UUID
from scripts.seed_inventory import seed
from app.inventory.operations import adjust_stock
from app.inventory.risk import inventory_view
from app.inventory.schemas import AdjustmentRequest, InventoryResponse
from app.inventory.schemas import ProductForecastResponse
from datetime import datetime, timedelta
from app.inventory.db import WIB
from app.inventory.optimization import optimize_procurement
from app.inventory.sales_history import import_sales_history
import httpx


@pytest.fixture
def isolated_settings():
    url = os.environ.get("ARUNA_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires disposable aruna_hardening database")
    info = conninfo_to_dict(url)
    if info.get("dbname") != "aruna_hardening" or not info.get("host", "").startswith("aruna-hardening-db-"):
        pytest.fail("Refusing mutation tests outside the disposable hardening database")
    with psycopg.connect(url) as connection:
        assert connection.execute("SELECT current_database()").fetchone()[0] == "aruna_hardening"
        connection.execute("DROP SCHEMA IF EXISTS aruna_inventory CASCADE")
        for migration in sorted((Path(__file__).resolve().parents[1] / "migrations").glob("*.sql")):
            connection.execute(migration.read_text(encoding="utf-8"))
    settings = Settings(
        app_env="test", inventory_database_url=SecretStr(url),
        openrouter_api_key=None, gemini_api_key=None, explanation_mode="deterministic",
    )
    seed(settings)
    return settings


def checkout(settings, product="P009", quantity=2, key=None):
    with connect(settings) as connection:
        return create_transaction(
            connection,
            CreateTransactionRequest(source="POS_SIMULATOR", items=[{"productId": product, "quantity": quantity}]),
            idempotency_key=key or str(uuid4()), correlation_id="hardening-test",
        )[1]


@pytest.mark.parametrize("invalid_kind", ["inactive", "unit"])
def test_partial_invalid_bom_never_commits_sale(isolated_settings, invalid_kind):
    settings = isolated_settings
    with connect(settings) as connection:
        connection.execute(
            "INSERT INTO inventory_recipe(product_id,ingredient_id,quantity_required_base) "
            "VALUES ('P009','ing_jeruk',100000)"
        )
        if invalid_kind == "inactive":
            connection.execute("UPDATE inventory_ingredient SET active=false WHERE id='ing_jeruk'")
        else:
            connection.execute("UPDATE inventory_ingredient SET storage_scale=1000 WHERE id='ing_jeruk'")
        before = balances_base(connection)
    with pytest.raises(ApiError) as error:
        checkout(settings)
    assert error.value.code == "INVALID_BOM"
    with connect(settings) as connection:
        assert connection.execute("SELECT count(*) AS n FROM inventory_sale").fetchone()["n"] == 0
        assert balances_base(connection) == before


def test_missing_bom_rejected_and_demo_scope_preserved(isolated_settings):
    result = checkout(isolated_settings)
    assert result["transaction"]["totalAmount"] == 40000
    assert result["transaction"]["ingredientConsumption"] == [
        {"ingredientId": "ing_stroberi", "ingredientName": "Stroberi", "quantity": 0.5, "unit": "kg"}
    ]
    with connect(isolated_settings) as connection:
        connection.execute("DELETE FROM inventory_recipe WHERE product_id='P010'")
    with pytest.raises(ApiError) as error:
        checkout(isolated_settings, product="P010")
    assert error.value.code == "MISSING_BOM"


def test_sale_approval_partial_and_final_receiving_across_plans(isolated_settings):
    settings = isolated_settings
    key = str(uuid4())
    first = checkout(settings, key=key)["transaction"]
    repeat = checkout(settings, key=key)["transaction"]
    assert first["id"] == repeat["id"]
    with connect(settings) as connection:
        assert connection.execute("SELECT count(*) AS n FROM inventory_sale").fetchone()["n"] == 1
        assert get_transaction(connection, UUID(first["id"]))["transaction"]["ingredientConsumption"][0]["quantity"] == 0.5
        assert balances_base(connection)["ing_stroberi"] == 9_500_000
        movements = list_movements(connection, ingredient_id="ing_stroberi", movement_type="SALE", page=1, page_size=100)
        assert len(movements["items"]) == 1
        assert movements["items"][0]["quantityChange"] == -0.5
        forecast = product_forecast(connection, settings, "P009", correlation_id="test")
        assert len(forecast["forecast"]) == 3
        assert forecast["ingredientRequirements"][0]["totalRequired"] > 0
        risks = evaluate_risks(connection, settings, correlation_id="test")
        assert next(r for r in risks["items"] if r["ingredientId"] == "ing_stroberi")["riskLevel"] == "HIGH"
        plan = recommendations(connection, settings, correlation_id="test")
        ProcurementResponse.model_validate(plan)
        original = next(r for r in plan["recommendations"] if r["ingredientId"] == "ing_stroberi")
        before_approval = balances_base(connection)
        decide(connection, UUID(original["id"]), "APPROVED", correlation_id="test")
        assert balances_base(connection) == before_approval

    def receive(quantity, receipt_key):
        with connect(settings) as connection:
            return stock_in(
                connection, "ing_stroberi",
                StockInRequest(
                    quantity=quantity, unit="kg", supplierId=original["supplier"]["id"],
                    recommendationId=original["id"], externalReceiptId=receipt_key,
                ), idempotency_key=receipt_key, correlation_id="test",
            )[1]

    receipt_key = str(uuid4())
    receive(2.5, receipt_key)
    receive(2.5, receipt_key)  # Replay must not receive twice.
    with connect(settings) as connection:
        assert balances_base(connection)["ing_stroberi"] == 12_000_000
        newer = recommendations(connection, settings, correlation_id="test")
        assert newer["planId"] != plan["planId"]
        carried = next(r for r in newer["outstandingRecommendations"] if r["id"] == original["id"])
        assert carried["planId"] == plan["planId"]
        assert carried["status"] == "APPROVED"
        assert carried["supplier"] == original["supplier"]
        assert carried["receivedQuantity"] == 2.5
        assert carried["outstandingQuantity"] == original["recommendedOrderQuantity"] - 2.5
        ProcurementResponse.model_validate(newer)
    receive(carried["outstandingQuantity"], str(uuid4()))
    with connect(settings) as connection:
        assert balances_base(connection)["ing_stroberi"] == 9_500_000 + round(original["recommendedOrderQuantity"] * 1_000_000)
        final_plan = recommendations(connection, settings, correlation_id="test")
        assert all(r["id"] != original["id"] for r in final_plan["outstandingRecommendations"])
        assert connection.execute(
            "SELECT count(*) AS n FROM inventory_stock_movement WHERE recommendation_id=%s AND movement_type='STOCK_IN'",
            (UUID(original["id"]),),
        ).fetchone()["n"] == 2
        print({"trace": "isolated sale-to-final-receiving", "saleCount": 1, "stockBeforeKg": 10, "deductedKg": 0.5, "stockAfterSaleKg": 9.5, "forecastSource": forecast["source"], "forecastCups": sum(point["predictedDemand"] for point in forecast["forecast"]), "requiredKg": forecast["ingredientRequirements"][0]["totalRequired"], "risk": "HIGH", "recommendedKg": original["recommendedOrderQuantity"], "stockAfterApprovalKg": before_approval["ing_stroberi"] / 1_000_000, "partiallyReceivedKg": 2.5, "stockAfterPartialKg": 12, "outstandingAfterNewPlanKg": carried["outstandingQuantity"], "stockAfterFinalKg": balances_base(connection)["ing_stroberi"] / 1_000_000})


def test_stocktaking_rejects_stale_count_then_accepts_reconciled_version(isolated_settings):
    settings = isolated_settings
    with connect(settings) as connection:
        counted = inventory_view(connection, settings, correlation_id="test", search=None, risk_level=None)
        InventoryResponse.model_validate(counted)
        adjustment_count = connection.execute("SELECT count(*) AS n FROM inventory_stock_movement WHERE movement_type='ADJUSTMENT'").fetchone()["n"]
    checkout(settings)
    with pytest.raises(ApiError) as error:
        with connect(settings) as connection:
            adjust_stock(connection, "ing_stroberi", AdjustmentRequest(countedStock=10, unit="kg", reason="PHYSICAL_COUNT", expectedInventoryVersion=counted["inventoryVersion"]), idempotency_key=str(uuid4()), correlation_id="test")
    assert error.value.code == "STALE_INVENTORY"
    with connect(settings) as connection:
        assert balances_base(connection)["ing_stroberi"] == 9_500_000
        assert connection.execute("SELECT count(*) AS n FROM inventory_stock_movement WHERE movement_type='ADJUSTMENT'").fetchone()["n"] == adjustment_count
        refreshed = inventory_view(connection, settings, correlation_id="test", search=None, risk_level=None)
        assert refreshed["inventoryVersion"] > counted["inventoryVersion"]
        adjust_stock(connection, "ing_stroberi", AdjustmentRequest(countedStock=9, unit="kg", reason="PHYSICAL_COUNT", expectedInventoryVersion=refreshed["inventoryVersion"]), idempotency_key=str(uuid4()), correlation_id="test")
        assert balances_base(connection)["ing_stroberi"] == 9_000_000


def test_multi_offer_solver_selects_one_offer_and_discloses_unmet_requirement():
    offers = [{"id": name, "ingredient_id": "fruit", "lead_time_hours": 24, "capacity_packs": 1, "minimum_packs": 1, "pack_quantity_base": 6, "pack_cost_idr": 1} for name in ("offer-a", "offer-b")]
    result = optimize_procurement(risks=[{"ingredientId": "fruit", "riskLevel": "HIGH", "_base": {"required": 10, "dailyRequired": [10, 0, 0], "safety": 0, "current": 0, "storageCapacity": 20}}], offers=offers, budget_idr=100)
    assert result["optimizerStatus"] == "OPTIMAL"
    assert len(result["selectedOffers"]) == 1
    assert result["unmet"]["fruit"] == 4
    assert result["planOutcome"] == "PARTIAL"


def test_multi_offer_plan_persists_with_current_unique_constraint(isolated_settings):
    settings = isolated_settings.model_copy(update={"inventory_procurement_budget_idr": 10_000_000})
    with connect(settings) as connection:
        connection.execute("UPDATE inventory_supplier_offer SET capacity_packs=1,pack_quantity_base=5000000,pack_cost_idr=1 WHERE ingredient_id='ing_stroberi'")
        connection.execute("INSERT INTO inventory_supplier(id,name,lead_time_hours) VALUES ('second-supplier','Second supplier',24)")
        connection.execute("INSERT INTO inventory_supplier_offer(id,supplier_id,ingredient_id,pack_quantity_base,pack_cost_idr,minimum_packs,capacity_packs) VALUES ('second-offer','second-supplier','ing_stroberi',5000000,1,1,1)")
        plan = recommendations(connection, settings, correlation_id="test")
        ProcurementResponse.model_validate(plan)
        fruit = [r for r in plan["recommendations"] if r["ingredientId"] == "ing_stroberi"]
        assert len(fruit) == 1
        assert fruit[0]["unmetQuantity"] > 0
        assert plan["planOutcome"] == "PARTIAL"
        assert connection.execute("SELECT count(*) AS n FROM inventory_recommendation WHERE plan_id=%s AND ingredient_id='ing_stroberi'", (UUID(plan["planId"]),)).fetchone()["n"] == 1


def test_qwen_timeout_preserves_usable_deterministic_recommendation(isolated_settings, monkeypatch):
    settings = isolated_settings.model_copy(update={"openrouter_api_key": SecretStr("isolated-test-not-a-real-key"), "explanation_mode": "auto"})
    def timeout(*_args, **_kwargs):
        raise httpx.ReadTimeout("Simulated provider timeout")
    monkeypatch.setattr("app.inventory.explanation.httpx.post", timeout)
    with connect(settings) as connection:
        plan = recommendations(connection, settings, correlation_id="test")
        ProcurementResponse.model_validate(plan)
        assert plan["recommendations"]
        for item in plan["recommendations"]:
            assert item["explanation"]["source"] == "FALLBACK"
            assert item["recommendedOrderQuantity"] > 0
            assert item["supplier"]["id"]
        original = plan["recommendations"][0]
        before = balances_base(connection)
        assert decide(connection, UUID(original["id"]), "APPROVED", correlation_id="test")["status"] == "APPROVED"
        assert balances_base(connection) == before


def days_ago(days):
    return datetime.now(WIB).date() - timedelta(days=days)


def history_csv(days, start_offset=1, product="P009", quantity=6):
    rows = [f"{days_ago(start_offset + index).isoformat()},{product},{quantity}" for index in range(days)]
    return ("date,product_id,quantity\n" + "\n".join(rows) + "\n").encode()


def import_history(connection, content, key=None):
    return import_sales_history(connection, content, filename="h.csv", idempotency_key=key, correlation_id="test")


@pytest.mark.parametrize("history_kind", ["synthetic", "observed", "single-old-sale", "imported"])
def test_forecast_provenance_distinguishes_training_runtime_and_history(isolated_settings, history_kind):
    settings = isolated_settings
    if history_kind in {"observed", "single-old-sale"}:
        checkout(settings)
    if history_kind == "single-old-sale":
        # One old sale is not a usable feature window; it must not unlock XGBoost.
        with connect(settings) as connection:
            connection.execute("UPDATE inventory_sale SET business_date=%s", (days_ago(30),))
    if history_kind == "imported":
        with connect(settings) as connection:
            import_history(connection, history_csv(29))
    with connect(settings) as connection:
        forecast = product_forecast(connection, settings, "P009", correlation_id="test")
        ProductForecastResponse.model_validate(forecast)
        model_ready = history_kind == "imported"
        assert forecast["trainingDataSynthetic"] is True
        assert forecast["source"] == ("XGBOOST" if model_ready else "FALLBACK")
        assert forecast["isSynthetic"] == (not model_ready)
        assert forecast["historyCoverage"]["coveredDays"] == (29 if model_ready else 0)
        expected_sources = {
            "synthetic": {"SYNTHETIC_DEMAND"},
            "observed": {"OBSERVED_SALES"},
            "single-old-sale": {"OBSERVED_SALES"},
            "imported": {"IMPORTED_SALES"},
        }[history_kind]
        assert {point["historySource"] for point in forecast["history"]} == expected_sources
        assert forecast["fallbackReason"] == (None if model_ready else "INSUFFICIENT_OBSERVED_SALES_HISTORY")


def test_sales_history_import_feeds_forecast_without_touching_stock(isolated_settings):
    settings = isolated_settings
    with connect(settings) as connection:
        before = balances_base(connection)
        version = connection.execute("SELECT inventory_version FROM inventory_state WHERE id=1").fetchone()
        first = import_history(connection, history_csv(20), key="k1")
        assert first["daysImported"] == 20 and first["coverage"]["ready"] is False
        assert first["coverage"]["coveredDays"] == 20
        assert import_history(connection, history_csv(20), key="k1")["batchId"] == first["batchId"]
        second = import_history(connection, history_csv(29, quantity=8))
        assert second["replacedDays"] == 20 and second["coverage"]["ready"] is True
        assert balances_base(connection) == before
        assert connection.execute("SELECT inventory_version FROM inventory_state WHERE id=1").fetchone() == version
        assert connection.execute("SELECT count(*) AS n FROM inventory_sale").fetchone()["n"] == 0
        quantities = connection.execute("SELECT DISTINCT quantity FROM inventory_sales_history").fetchall()
        assert quantities == [{"quantity": 8}]


def test_sales_history_import_rejects_dates_already_recorded_by_pos(isolated_settings):
    settings = isolated_settings
    checkout(settings)
    with connect(settings) as connection:
        connection.execute("UPDATE inventory_sale SET business_date=%s", (days_ago(3),))
    with pytest.raises(ApiError) as error, connect(settings) as connection:
        import_history(connection, history_csv(5))
    assert error.value.code == "SALES_HISTORY_OVERLAPS_POS"
    with connect(settings) as connection:
        assert connection.execute("SELECT count(*) AS n FROM inventory_sales_history").fetchone()["n"] == 0
