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
    id: str
    label: str


class RoadSegmentRisk(ApiModel):
    segment_id: str
    road_name: str
    geometry: GeoLineString
    risk_probability: float
    risk_level: Literal["low", "medium", "high", "critical"]
    estimated_delay_minutes: int | None = None
    risk_factors: list[RiskFactor]
    affected_supplier_ids: list[str]
    affected_warehouse_ids: list[str]
    affected_order_ids: list[str]


class RouteAnalysis(ApiModel):
    id: str
    type: Literal["baseline", "recovery"]
    origin_facility_id: str
    destination_facility_id: str
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
    subject: str
    description: str


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
