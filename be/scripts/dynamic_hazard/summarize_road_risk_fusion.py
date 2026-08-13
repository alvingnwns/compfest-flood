from __future__ import annotations

import json

from dynamic_hazard.analyze_road_risk_fusion import DEFAULT_OUTPUT_DIR


def main() -> None:
    analysis = json.loads((DEFAULT_OUTPUT_DIR / "fusion_analysis.json").read_text(encoding="utf-8"))
    selected = analysis["selectedCandidate"]
    record = next(
        row
        for row in analysis["candidates"]
        if row["method"] == selected["method"] and row["parameter"] == selected["parameter"]
    )
    print(f"Selected: {selected['method']} parameter={selected['parameter']}")
    for scenario in record["scenarioResults"]:
        distribution = scenario["distribution"]
        categories = scenario["categoryCounts"]
        print(
            f"{scenario['scenario']}: median={distribution['median']:.4f}, "
            f"categories={categories}, changedOD={scenario['routing']['changedFromBaselineCount']}"
        )
    print(f"Q1->Q4: {record['scoreShifts']['Q1_to_Q4']}")
    print(f"Routing Q1->Q4: {record['routingTransitions']['Q1_to_Q4']}")


if __name__ == "__main__":
    main()
