from __future__ import annotations

import math
from typing import Any


def operational_metrics(
    *,
    demanded_cups: int,
    fulfilled_cups: int,
    purchase_cost_idr: int,
    holding_cost_idr: int,
    stockout_cost_idr: int,
    waste_cost_idr: int,
    violations: list[dict[str, Any]],
    constraint_checks: int,
) -> dict[str, Any]:
    unfulfilled = demanded_cups - fulfilled_cups
    return {
        "actualDemandCups": demanded_cups,
        "fulfilledDemandCups": fulfilled_cups,
        "serviceLevelPercent": round(fulfilled_cups / demanded_cups * 100, 6)
        if demanded_cups
        else 100.0,
        "unfulfilledDemandCups": unfulfilled,
        "totalOperationalCostIdr": purchase_cost_idr
        + holding_cost_idr
        + stockout_cost_idr
        + waste_cost_idr,
        "costBreakdownIdr": {
            "purchase": purchase_cost_idr,
            "holding": holding_cost_idr,
            "stockout": stockout_cost_idr,
            "waste": waste_cost_idr,
        },
        "constraintViolationRatePercent": round(
            len(violations) / constraint_checks * 100, 6
        )
        if constraint_checks
        else None,
        "constraintChecks": constraint_checks,
        "constraintViolations": violations,
    }


def forecast_diagnostics(
    predicted: list[int], actual: list[int]
) -> dict[str, float | int]:
    if len(predicted) != len(actual) or not actual:
        raise ValueError("Forecast diagnostic vectors must be non-empty and aligned")
    errors = [
        prediction - observation
        for prediction, observation in zip(predicted, actual, strict=True)
    ]
    return {
        "observations": len(errors),
        "maeCups": round(sum(abs(error) for error in errors) / len(errors), 6),
        "rmseCups": round(
            math.sqrt(sum(error * error for error in errors) / len(errors)), 6
        ),
    }
