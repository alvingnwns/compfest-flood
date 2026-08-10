from __future__ import annotations

from typing import Any

from app.schemas.common import ApiModel
from app.schemas.disruption import Money


class KpiMetric(ApiModel):
    key: str
    baseline: float
    recovery: float
    total: float | None = None
    currency: str | None = None


class ActionCounts(ApiModel):
    manufacturing: int
    logistics: int
    commerce: int


class ImpactComparison(ApiModel):
    simulation_id: str
    metrics: list[KpiMetric]
    action_counts: ActionCounts
