from __future__ import annotations

import math

from app.errors import ApiError

FUSION_METHOD = "logit_shift"
FUSION_BETA = 1.5
LOGIT_EPSILON = 1e-9


def dynamic_road_risk_score(static_road_susceptibility: float, relative_hazard_index: float) -> float:
    if not math.isfinite(static_road_susceptibility) or not 0 <= static_road_susceptibility <= 1:
        raise ApiError(422, "DYNAMIC_HAZARD_RUNTIME_ERROR", "Static road susceptibility tidak valid.")
    if not math.isfinite(relative_hazard_index) or not 0 <= relative_hazard_index <= 1:
        raise ApiError(422, "DYNAMIC_HAZARD_RUNTIME_ERROR", "Relative hazard index tidak valid.")
    clipped = min(max(static_road_susceptibility, LOGIT_EPSILON), 1 - LOGIT_EPSILON)
    logit = math.log(clipped / (1 - clipped))
    result = 1 / (1 + math.exp(-(logit + FUSION_BETA * relative_hazard_index)))
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ApiError(500, "DYNAMIC_HAZARD_RUNTIME_ERROR", "Dynamic road risk fusion menghasilkan skor tidak valid.")
    return result


def routing_band(score: float) -> str:
    """Compatibility band using unchanged static-model thresholds; not validated flood severity."""
    if score < 0.25:
        return "low"
    if score < 0.5:
        return "medium"
    if score < 0.75:
        return "high"
    return "critical"
