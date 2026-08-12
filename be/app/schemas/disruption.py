from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel, LineGeometry, Money, PolygonalGeometry, RiskLevel
from app.schemas.scenario import Facility


class RiskFactor(ApiModel):
    id: str
    label: str


class RoadRisk(ApiModel):
    segment_id: str
    road_name: str
    highway_class: str | None = None
    osm_way_ids: list[str] = Field(default_factory=list)
    geometry: LineGeometry
    risk_probability: float = Field(ge=0, le=1)
    risk_level: RiskLevel
    estimated_delay_minutes: float = Field(ge=0)
    risk_factors: list[RiskFactor]
    affected_supplier_ids: list[str]
    affected_warehouse_ids: list[str]
    affected_order_ids: list[str]


class Route(ApiModel):
    id: str
    type: Literal["baseline", "recovery"]
    origin_facility_id: str
    destination_facility_id: str
    geometry: LineGeometry
    distance_km: float = Field(gt=0)
    eta_minutes: float = Field(gt=0)
    flood_exposure: RiskLevel
    flood_exposure_probability: float = Field(ge=0, le=1)
    affected_road_segment_ids: list[str]


class PrioritizedIssue(ApiModel):
    id: str
    severity: RiskLevel
    subject: str
    description: str


class OperationalImpact(ApiModel):
    impacted_supplier_ids: list[str]
    impacted_warehouse_ids: list[str]
    impacted_order_ids: list[str]
    road_segments_at_risk: int = Field(ge=0)
    sales_exposure: Money
    issues: list[PrioritizedIssue]


class DisruptionAnalysis(ApiModel):
    simulation_id: str
    facilities: list[Facility]
    roads: list[RoadRisk]
    routes: list[Route]
    historical_flood_geometry: PolygonalGeometry | None = None
    impact: OperationalImpact
