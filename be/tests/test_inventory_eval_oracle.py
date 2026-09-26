from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval.oracle import oracle_diagnostics  # noqa: E402
from eval.simulator import simulate  # noqa: E402

CUP = 250_000


def _output(decisions):
    offers = [
        {
            "id": f"late:{ingredient_id}",
            "template_id": "late",
            "ingredient_id": ingredient_id,
            "supplier_id": "SUP",
            "lead_time_hours": 48,
            "pack_quantity_base": 4 * CUP,
            "minimum_packs": 1,
            "capacity_packs": 2,
            "pack_cost_idr": 10_000,
        }
        for ingredient_id in ("ING-1", "ING-2")
    ]
    return {
        "productIds": ["P1", "P2"],
        "ingredientByProduct": {"P1": "ING-1", "P2": "ING-2"},
        "actualDemand": {"P1": [4, 0, 0], "P2": [0, 0, 4]},
        "predictions": {"P1": [4, 0, 0], "P2": [0, 0, 4]},
        "offers": offers,
        "decisions": decisions,
        "input": {
            "initialStockBase": 0,
            "storageCapacityBase": 20 * CUP,
            "recipeBasePerCup": CUP,
            "budgetIdr": 10_000,
            "stockoutCostIdrPerCup": 20_000,
            "holdingCostIdrPerKgDay": 0,
        },
    }


def test_oracle_bounds_and_regret_use_simulator_semantics() -> None:
    # The system bought for P1, whose only demand is on day 1, before any day-2 arrival can help.
    wasted = {
        "ingredientId": "ING-1",
        "offerId": "late",
        "supplierId": "SUP",
        "packCount": 1,
        "packQuantityBase": 4 * CUP,
        "quantityBase": 4 * CUP,
        "minimumPacks": 1,
        "capacityPacks": 2,
        "packCostIdr": 10_000,
        "totalCostIdr": 10_000,
        "leadTimeHours": 48,
    }
    output = _output([wasted])
    system = simulate(output)["metrics"]
    oracle = oracle_diagnostics(output, system)

    assert system["fulfilledDemandCups"] == 0
    assert oracle["oracleMaximumFulfilledCups"] == 4
    assert oracle["serviceRegretCups"] == 4
    assert oracle["feasibleFulfillmentPercent"] == 0.0
    assert oracle["oracleMinimumCostIdr"] == 10_000 + 4 * 20_000
    assert oracle["operationalCostRegretIdr"] == system["totalOperationalCostIdr"] - oracle["oracleMinimumCostIdr"]
    assert [d["ingredientId"] for d in oracle["oracleDecisions"]["maximumFulfillment"]] == ["ING-2"]


def test_oracle_reports_undefined_ratio_when_nothing_is_achievable() -> None:
    output = _output([])
    output["input"]["budgetIdr"] = 0
    oracle = oracle_diagnostics(output, simulate(output)["metrics"])
    assert oracle["oracleMaximumFulfilledCups"] == 0
    assert oracle["feasibleFulfillmentPercent"] is None
    assert oracle["serviceRegretCups"] == 0
