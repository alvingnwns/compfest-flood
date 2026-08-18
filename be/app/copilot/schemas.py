from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel, RiskLevel


class CopilotConversationMessage(ApiModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2_000)


class CopilotRequest(ApiModel):
    message: str = Field(min_length=1, max_length=1_000)
    recent_messages: list[CopilotConversationMessage] = Field(default_factory=list, max_length=6)


class HazardContext(ApiModel):
    rainfall_scenario: str
    relative_hazard_index: float
    temporal_hazard_score: float
    probability_calibrated: bool
    semantics: str


class RoadContext(ApiModel):
    segment_id: str
    road_name: str
    risk_level: RiskLevel
    risk_score: float
    score_semantics: str
    affected_supplier_ids: list[str]
    affected_warehouse_ids: list[str]
    affected_order_ids: list[str]


class RouteContext(ApiModel):
    route_id: str
    route_type: Literal["baseline", "recovery"]
    origin: str
    destination: str
    eta_minutes: float
    flood_exposure: RiskLevel
    exposure_score: float
    affected_road_segment_ids: list[str]


class IssueContext(ApiModel):
    severity: RiskLevel
    subject: str
    description: str


class RecoveryActionContext(ApiModel):
    category: Literal["manufacturing", "logistics", "commerce"]
    entity_id: str
    what: str
    why: str
    expected_impact: str


class KpiContext(ApiModel):
    key: str
    baseline: float
    recovery: float
    total: float | None = None
    currency: str | None = None


class CopilotContext(ApiModel):
    simulation_id: str
    scenario_id: str
    scenario_name: str
    business_data_source: Literal["demo", "custom"]
    analysis_mode: Literal["historical-replay", "scenario-simulation"]
    region: str
    model_version: str | None
    optimizer_version: str | None
    hazard: HazardContext | None
    affected_roads: list[RoadContext]
    routes: list[RouteContext]
    selected_recovery_route_ids: list[str] = Field(default_factory=list)
    impacted_suppliers: list[str]
    impacted_warehouses: list[str]
    impacted_orders: list[str]
    road_segments_at_risk: int
    disruption_sales_exposure: float
    disruption_sales_exposure_currency: str
    prioritized_issues: list[IssueContext]
    recovery_status: str | None
    recovery_summary: dict[str, int] | None
    recovery_actions: list[RecoveryActionContext]
    kpis: list[KpiContext]


class CopilotProviderOutput(ApiModel):
    answer: str = Field(min_length=1, max_length=4_000)


class CopilotResponse(ApiModel):
    answer: str
    provider: Literal["gemini", "qwen", "deterministic"]
    grounded: Literal[True] = True
    suggested_questions: list[str]
    fallback_reason: str | None = None
