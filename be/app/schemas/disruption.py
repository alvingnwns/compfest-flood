<<<<<<< HEAD
from __future__ import annotations

from typing import Any, Literal

from app.schemas.common import ApiModel
from app.schemas.scenario import Facility


class GeoLineString(ApiModel):
    type: Literal["LineString"]
    coordinates: list[tuple[float, float]]


class GeoMultiLineString(ApiModel):
    type: Literal["MultiLineString"]
    coordinates: list[list[tuple[float, float]]]


class RiskFactor(ApiModel):
=======
from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel, LineGeometry, Money, PolygonalGeometry, RiskLevel
from app.schemas.scenario import Facility


class RiskFactor(APIModel):
>>>>>>> 920f8995c90025b5acc284e9377e3e9b5660cb39
    id: str
    label: str


<<<<<<< HEAD
class RoadSegmentRisk(ApiModel):
    segment_id: str
    road_name: str
    geometry: GeoLineString
    risk_probability: float
    risk_level: Literal["low", "medium", "high", "critical"]
    estimated_delay_minutes: int | None = None
=======
class RoadRisk(APIModel):
    segment_id: str
    road_name: str
    geometry: LineGeometry
    risk_probability: float = Field(ge=0, le=1)
    risk_level: RiskLevel
    estimated_delay_minutes: float = Field(ge=0)
>>>>>>> 920f8995c90025b5acc284e9377e3e9b5660cb39
    risk_factors: list[RiskFactor]
    affected_supplier_ids: list[str]
    affected_warehouse_ids: list[str]
    affected_order_ids: list[str]


<<<<<<< HEAD
class RouteAnalysis(ApiModel):
=======
class Route(APIModel):
>>>>>>> 920f8995c90025b5acc284e9377e3e9b5660cb39
    id: str
    type: Literal["baseline", "recovery"]
    origin_facility_id: str
    destination_facility_id: str
<<<<<<< HEAD
    geometry: GeoLineString | GeoMultiLineString
    distance_km: float
    eta_minutes: int
    flood_exposure: Literal["low", "medium", "high", "critical"]
    flood_exposure_probability: float
    affected_road_segment_ids: list[str]


class Money(ApiModel):
    amount: float
    currency: str


class Issue(ApiModel):
    id: str
    severity: Literal["low", "medium", "high", "critical"]
=======
    geometry: LineGeometry
    distance_km: float = Field(gt=0)
    eta_minutes: float = Field(gt=0)
    flood_exposure: RiskLevel
    flood_exposure_probability: float = Field(ge=0, le=1)
    affected_road_segment_ids: list[str]


class PrioritizedIssue(APIModel):
    id: str
    severity: RiskLevel
>>>>>>> 920f8995c90025b5acc284e9377e3e9b5660cb39
    subject: str
    description: str


<<<<<<< HEAD
class ImpactSummary(ApiModel):
    impacted_supplier_ids: list[str]
    impacted_warehouse_ids: list[str]
    impacted_order_ids: list[str]
    road_segments_at_risk: int
    sales_exposure: Money
    issues: list[Issue]


class DisruptionAnalysis(ApiModel):
    simulation_id: str
    facilities: list[Facility]
    historical_flood_geometry: dict[str, Any]
    roads: list[RoadSegmentRisk]
    routes: list[RouteAnalysis]
    impact: ImpactSummary
=======
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
>>>>>>> 920f8995c90025b5acc284e9377e3e9b5660cb39
