from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dynamic_hazard.analyze_supply_chain_propagation import (
    CONDITION_ORDER,
    SCENARIOS,
    run_analysis,
)

BE_DIR = Path(__file__).resolve().parents[1]
PHASE5A_DIR = BE_DIR / "artifacts" / "dynamic-hazard" / "experiments" / "phase5a"


def _strict_json(name: str) -> dict:
    return json.loads(
        (PHASE5A_DIR / name).read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _row_index(matrix: dict) -> dict[tuple[str, str], dict]:
    return {(row["conditionId"], row["rainfallScenario"]): row for row in matrix["rows"]}


def test_matrix_covers_all_16_controlled_combinations() -> None:
    matrix = _strict_json("propagation_matrix.json")
    assert matrix["combinationCount"] == 16
    assert set(_row_index(matrix)) == {(condition, scenario) for condition in CONDITION_ORDER for scenario in SCENARIOS}
    assert matrix["independence"] == {
        "hazardIndependentOfOperationalCondition": True,
        "operationalStateIndependentOfRainfallScenario": True,
    }
    assert matrix["routingToOptimizerContract"]["routeIdOnly"] is False


def test_hazard_and_road_risk_are_monotonic_while_networkx_is_valid() -> None:
    matrix = _strict_json("propagation_matrix.json")
    index = _row_index(matrix)
    for condition in CONDITION_ORDER:
        hazard = [index[condition, scenario]["hazard"]["relativeHazardIndex"] for scenario in SCENARIOS]
        median = [index[condition, scenario]["roadRisk"]["median"] for scenario in SCENARIOS]
        assert all(lower < upper for lower, upper in zip(hazard, hazard[1:], strict=False))
        assert all(lower < upper for lower, upper in zip(median, median[1:], strict=False))
        for scenario in SCENARIOS:
            row = index[condition, scenario]
            assert row["roadRisk"]["count"] == 1413
            assert row["routing"]["odPairCount"] == 12
            assert row["routing"]["unreachableCount"] == 0
        q1 = {
            (route["origin"], route["destination"]): route["segmentPathSha256"]
            for route in index[condition, "Q1"]["routing"]["selectedRoutes"]
        }
        q4 = {
            (route["origin"], route["destination"]): route["segmentPathSha256"]
            for route in index[condition, "Q4"]["routing"]["selectedRoutes"]
        }
        assert sum(q1[pair] != q4[pair] for pair in q1) == 9


def test_all_optimizer_integrity_checks_pass() -> None:
    matrix = _strict_json("propagation_matrix.json")
    for row in matrix["rows"]:
        assert row["recovery"]["solverFeasible"] is True
        assert row["recovery"]["solverStatus"] in {"ready", "partial"}
        assert row["optimizerIntegrity"]["allPassed"] is True
        assert all(row["optimizerIntegrity"]["checks"].values())


def test_binding_and_kpi_findings_are_computed_not_forced() -> None:
    matrix = _strict_json("propagation_matrix.json")
    traces = _strict_json("causal_traces.json")["traces"]
    gate = _strict_json("decision_gate.json")
    index = _row_index(matrix)
    classifications = {(row["conditionId"], row["rainfallScenario"]): row["classification"] for row in traces}
    assert gate["decision"] == "CONDITIONAL GO"
    assert gate["bindingCounts"] == {"BINDING": 7, "NON_BINDING": 4, "PARTIALLY_BINDING": 5}
    assert classifications["critical-stock", "Q3"] == "BINDING"
    assert classifications["severe-disruption", "Q4"] == "PARTIALLY_BINDING"
    critical_q1 = index["critical-stock", "Q1"]
    critical_q3 = index["critical-stock", "Q3"]
    assert critical_q1["recovery"]["production"] == {"prod-a": 450, "prod-b": 50}
    assert critical_q3["recovery"]["production"] == {"prod-a": 330, "prod-b": 170}
    assert critical_q1["kpi"]["orders-fulfilled"]["recovery"] == 14
    assert critical_q3["kpi"]["orders-fulfilled"]["recovery"] == 11
    assert critical_q1["kpi"]["sales-exposure-risk"]["recovery"] == 50_000_000
    assert critical_q3["kpi"]["sales-exposure-risk"]["recovery"] == 62_800_000
    severe_kpis = [index["severe-disruption", scenario]["kpi"] for scenario in SCENARIOS]
    assert all(value == severe_kpis[0] for value in severe_kpis[1:])


def test_historical_simulation_recovery_and_kpi_remain_frozen() -> None:
    historical = _strict_json("propagation_matrix.json")["historicalRegression"]
    assert historical["goldenMatches"] is True
    assert historical["dynamicHazardAbsent"] is True
    assert historical["recoveryCanonicalSha256"] == ("92118e10507566d84a0c9d7d1b53dc7b2e3f1c45c6cf50128f3edaed0467823a")
    assert historical["kpiCanonicalSha256"] == ("6a52eaaad9711ecfc163323fb11caaf11767bfad6c28fc8ddaf7380c7e3fa3da")


def test_analysis_artifacts_are_byte_reproducible(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    run_analysis(first)
    run_analysis(second)
    expected = {
        "propagation_matrix.json",
        "propagation_matrix.csv",
        "causal_traces.json",
        "decision_gate.json",
    }
    assert {path.name for path in first.iterdir()} == expected
    assert {path.name for path in second.iterdir()} == expected
    for name in expected:
        assert (
            hashlib.sha256((first / name).read_bytes()).hexdigest()
            == hashlib.sha256((second / name).read_bytes()).hexdigest()
        )
