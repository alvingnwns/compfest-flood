from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel


class RecoveryConstraints(ApiModel):
    allow_substitution: bool = False
    max_additional_delay_minutes: int | None = None


class RecoveryRequest(ApiModel):
    constraints: RecoveryConstraints | None = None


class RecoverySummary(ApiModel):
    risks_mitigated: int
    operational_changes: int
    recoverable_orders: int
    total_orders: int


class RecoveryAction(ApiModel):
    id: str
    what: str
    why: str
    expected_impact: str


class ManufacturingAction(RecoveryAction):
    product_id: str
    product_name: str
    baseline_quantity: int
    recovery_quantity: int
    change_quantity: int


class LogisticsAction(RecoveryAction):
    order_id: str
    original_warehouse_id: str
    original_warehouse_name: str
    recovery_warehouse_id: str
    recovery_warehouse_name: str
    vehicle_id: str
    baseline_route_id: str | None = None
    recovery_route_id: str | None = None
    baseline_eta_minutes: int | None = None
    recovery_eta_minutes: int | None = None
    baseline_flood_exposure: Literal["low", "medium", "high", "critical"] | None = None
    recovery_flood_exposure: Literal["low", "medium", "high", "critical"] | None = None
    action: Literal["reallocate-reroute", "reroute", "reallocate", "keep"]


class CommerceAllocation(ApiModel):
    product_id: str
    product_name: str
    quantity: int


class CommerceAction(RecoveryAction):
    order_id: str
    store_id: str
    store_name: str
    requested_product_id: str
    requested_product_name: str
    requested_quantity: int
    action: Literal["split-substitute", "delay", "fulfill", "fail"]
    allocations: list[CommerceAllocation]


class RecoveryResult(ApiModel):
    id: str
    simulation_id: str
    status: Literal["queued", "processing", "ready", "partial", "no-feasible-plan", "failed"]
    created_at: datetime
    completed_at: datetime | None = None
    summary: RecoverySummary | None = None
    manufacturing_actions: list[ManufacturingAction] | None = None
    logistics_actions: list[LogisticsAction] | None = None
    commerce_actions: list[CommerceAction] | None = None
    possible_next_actions: list[str] | None = None
    error: dict[str, str] | None = None
