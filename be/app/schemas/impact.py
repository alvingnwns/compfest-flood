from __future__ import annotations

from typing import Literal

from app.schemas.common import ApiModel


class KpiMetric(ApiModel):
    key: Literal["orders-fulfilled", "on-time-delivery", "failed-orders", "average-delay", "sales-exposure-risk"]
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
