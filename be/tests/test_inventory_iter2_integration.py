from __future__ import annotations

import json
from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.inventory.forecast import validation_mae_by_horizon
from app.inventory.optimization import OPTIMIZER_VERSION, optimize_procurement
from app.inventory.procurement import _approved_incoming_by_day
from app.inventory.risk import public_risks


def risk(daily):
    return {
        "ingredientId": "fruit",
        "riskLevel": "STOCKOUT",
        "_base": {
            "current": 0, "required": sum(daily), "dailyRequired": daily,
            "safety": 0, "storageCapacity": 100, "lostSalesIdrPerBase": 1, "priorityRank": 1,
        },
    }


def test_approved_commitments_are_bucketed_by_wib_arrival_and_remaining_quantity():
    connection = MagicMock()
    connection.execute.return_value.fetchall.return_value = [
        {"ingredient_id": "fruit", "expected_arrival_at": datetime(2026, 9, 24, 0, tzinfo=UTC), "outstanding": 2},
        {"ingredient_id": "fruit", "expected_arrival_at": datetime(2026, 9, 26, 17, tzinfo=UTC), "outstanding": 3},
        {"ingredient_id": "fruit", "expected_arrival_at": datetime(2026, 9, 27, 17, tzinfo=UTC), "outstanding": 7},
        {"ingredient_id": "fruit", "expected_arrival_at": datetime(2026, 9, 29, 17, tzinfo=UTC), "outstanding": 11},
    ]
    incoming, late = _approved_incoming_by_day(connection, date(2026, 9, 26))
    assert incoming == {"fruit": {1: 5, 2: 7}}
    assert late == {"fruit": 11}
    sql = connection.execute.call_args.args[0]
    assert "received_quantity_base" in sql and "status='APPROVED'" in sql


def test_unconfirmed_arrival_cannot_cover_an_earlier_shortage():
    result = optimize_procurement(
        risks=[risk([5, 5, 0])], offers=[], budget_idr=100,
        incoming_by_day={"fruit": {2: 10}},
    )
    assert result["planOutcome"] == "PARTIAL"
    assert result["unmet"]["fruit"] == 5
    assert result["dailyPlan"]["fruit"][0]["incomingBase"] == 0
    assert result["dailyPlan"]["fruit"][0]["shortageBase"] == 5
    assert result["dailyPlan"]["fruit"][1]["incomingBase"] == 10
    assert "APPROVED_QUANTITY_UNCONFIRMED:fruit:10" in result["limitations"]


def test_offer_arriving_outside_the_actual_wib_horizon_is_not_selected():
    offer = {
        "id": "late", "ingredient_id": "fruit", "lead_time_hours": 72,
        "pack_quantity_base": 10, "pack_cost_idr": 1, "minimum_packs": 1, "capacity_packs": 10,
    }
    result = optimize_procurement(
        risks=[risk([0, 0, 10])], offers=[offer], budget_idr=100,
        arrival_day_by_offer={"late": 4},
    )
    assert result["selectedOffers"] == []
    assert result["unmet"]["fruit"] == 10
    assert result["planOutcome"] == "PARTIAL"


def test_single_offer_adaptation_has_a_distinct_cache_version():
    assert OPTIMIZER_VERSION == "time-indexed-lexicographic-v2-single-offer"


def test_optimizer_requires_a_complete_daily_requirement():
    with pytest.raises(ValueError, match="must cover 3 days"):
        optimize_procurement(risks=[risk([10])], offers=[], budget_idr=100)


def test_uncertainty_reads_validation_not_frozen_test_metrics(tmp_path):
    metrics = {
        f"d{horizon}": {
            "validation": {"xgboostMae": horizon, "persistenceMae": horizon + 10},
            "test": {"xgboostMae": 999, "persistenceMae": 999},
        }
        for horizon in (1, 2, 3)
    }
    (tmp_path / "manifest.json").write_text(json.dumps({"metrics": metrics}), encoding="utf-8")
    settings = Settings(app_env="test", inventory_database_url=None, inventory_model_dir=tmp_path)
    assert validation_mae_by_horizon(settings) == [1, 2, 3]
    assert validation_mae_by_horizon(settings, fallback=True) == [11, 12, 13]


def test_internal_priority_does_not_change_the_public_risk_contract():
    data = public_risks({
        "generatedAt": "2026-09-26T00:00:00Z", "horizonDays": 3,
        "items": [{"ingredientId": "fruit", "riskLevel": "HIGH", "incomingStock": 0, "_base": {"priorityRank": 1}}],
    })
    assert data["items"] == [{"ingredientId": "fruit", "riskLevel": "HIGH", "incomingStock": 0}]
