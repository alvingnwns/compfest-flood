from __future__ import annotations

import math

from app.errors import ApiError
from app.services.rainfall_scenario_service import RainfallScenario

SCORE_ABSOLUTE_TOLERANCE = 1e-12


def relative_hazard_index(scenario: RainfallScenario, temporal_hazard_score: float) -> float:
    """Resolve the frozen train-derived scenario anchor after verifying runtime inference."""
    if not math.isfinite(temporal_hazard_score):
        raise ApiError(422, "TEMPORAL_MODEL_INPUT_INVALID", "Temporal hazard score harus finite.")
    if not math.isclose(
        temporal_hazard_score,
        scenario.temporal_hazard_score_research,
        rel_tol=0,
        abs_tol=SCORE_ABSOLUTE_TOLERANCE,
    ):
        raise ApiError(
            500,
            "DYNAMIC_HAZARD_RUNTIME_ERROR",
            "Temporal hazard score tidak cocok dengan frozen scenario anchor.",
            details={"rainfallScenario": scenario.id},
        )
    return scenario.relative_hazard_index
