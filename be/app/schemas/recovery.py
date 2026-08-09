from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from app.schemas.common import APIModel, ErrorResponse, RiskLevel


class Recommendation(APIModel):
    what: str
    why: str
    expected_impact: str


class ManufacturingAction(Recommendation):
    id: str
    product_id: str
    product_name: str
    baseline_quantity: float = Field(ge=0)
    recovery_quantity: float = Field(ge=0)
    change_quantity: float


class LogisticsAction(Recommendation):
    id: str
    order_id: str
    original_warehouse_id: str
    original_warehouse_name: str
    recovery_warehouse_id: str
    recovery_warehouse_name: str
    vehicle_id: str
    baseline_route_id: str
    recovery_route_id: str
    baseline_eta_minutes: float = Field(ge=0)
    recovery_eta_minutes: float = Field(ge=0)
    baseline_flood_exposure: RiskLevel
    recovery_flood_exposure: RiskLevel
    action: Literal["reallocate", "reroute", "reallocate-reroute"]


class Allocation(APIModel):
    product_id: str
    product_name: str
    quantity: float = Field(ge=0)


class CommerceAction(Recommendation):
    id: str
    order_id: str
    store_id: str
    store_name: str
    requested_product_id: str
    requested_product_name: str
    requested_quantity: float = Field(gt=0)
    action: Literal["fulfill", "split", "delay", "substitute", "prioritize", "split-substitute"]
    allocations: list[Allocation]


class RecoveryConstraints(APIModel):
    allow_substitution: bool | None = None
    max_additional_delay_minutes: float | None = Field(default=None, ge=0)


class RecoveryGenerationRequest(APIModel):
    constraints: RecoveryConstraints | None = None


class RecoveryBase(APIModel):
    id: str
    simulation_id: str
    created_at: datetime


class RecoveryPending(RecoveryBase):
    status: Literal["queued", "processing"]


class RecoveryFailed(RecoveryBase):
    status: Literal["failed"]
    error: ErrorResponse


class RecoverySummary(APIModel):
    risks_mitigated: int = Field(ge=0)
    operational_changes: int = Field(ge=0)
    recoverable_orders: int = Field(ge=0)
    total_orders: int = Field(ge=0)


class RecoveryResult(RecoveryBase):
    status: Literal["ready", "partial", "no-feasible-plan"]
    completed_at: datetime
    summary: RecoverySummary
    manufacturing_actions: list[ManufacturingAction]
    logistics_actions: list[LogisticsAction]
    commerce_actions: list[CommerceAction]
    possible_next_actions: list[str]


RecoveryPlan = Annotated[RecoveryPending | RecoveryFailed | RecoveryResult, Field(discriminator="status")]
