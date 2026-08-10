from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel, LineGeometry, Money, PolygonalGeometry, RiskLevel
from app.schemas.scenario import Facility


class RiskFactor(APIModel):
    id: str
    label: str


class RoadRisk(APIModel):
    segment_id: str
    road_name: str
    geometry: LineGeometry
    risk_probability: float = Field(ge=0, le=1)
    risk_level: RiskLevel
    estimated_delay_minutes: float = Field(ge=0)
    risk_factors: list[RiskFactor]
    affected_supplier_ids: list[str]
    affected_warehouse_ids: list[str]
    affected_order_ids: list[str]


class Route(APIModel):
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


class PrioritizedIssue(APIModel):
    id: str
    severity: RiskLevel
    subject: str
    description: str


class OperationalImpact(APIModel):
    impacted_supplier_ids: list[str]
    impacted_warehouse_ids: list[str]
    impacted_order_ids: list[str]
    road_segments_at_risk: int = Field(ge=0)
    sales_exposure: Money
    issues: list[PrioritizedIssue]


class DisruptionAnalysis(APIModel):
    simulation_id: str
    facilities: list[Facility]
    roads: list[RoadRisk]
    routes: list[Route]
    historical_flood_geometry: PolygonalGeometry | None = None
    impact: OperationalImpact
