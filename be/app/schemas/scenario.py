from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel


class GeoPoint(ApiModel):
    type: Literal["Point"]
    coordinates: tuple[float, float]


class Facility(ApiModel):
    id: str
    name: str
    kind: Literal["supplier", "factory", "warehouse", "store"]
    location: GeoPoint
    production_capacity_units: int | None = Field(default=None, gt=0)


class Vehicle(ApiModel):
    id: str
    label: str
    capacity_units: int = Field(gt=0)
    available: bool = True
    cost_per_km: float = Field(default=0, ge=0)


class BomItem(ApiModel):
    material_id: str
    quantity_per_unit: float = Field(gt=0)


class Product(ApiModel):
    id: str
    name: str
    unit: str
    unit_price: float = Field(ge=0)
    bom: list[BomItem] = Field(min_length=1)
    substitute_product_ids: list[str] = Field(default_factory=list)


class Material(ApiModel):
    id: str
    name: str
    supplier_id: str
    product_ids: list[str] = Field(min_length=1)
    available_quantity: float = Field(ge=0)


class Inventory(ApiModel):
    facility_id: str
    product_id: str
    quantity: float = Field(ge=0)
    unit: str


class Order(ApiModel):
    id: str
    store_id: str
    product_id: str
    quantity: int = Field(gt=0)
    priority: Literal["normal", "high", "critical"]
    preferred_warehouse_id: str
    deadline_minutes: int = Field(ge=0)


class DataSources(ApiModel):
    mode: Literal["historical_snapshot", "live", "hybrid"]
    historical_status: Literal["available", "offline_snapshot", "unavailable"]
    operational_status: Literal["simulated", "live"]
    historical_provider: str
    snapshot_id: str | None = None


class Scenario(ApiModel):
    id: str
    name: str
    mode: Literal["historical-replay"]
    location: str
    event_date: date
    event_type: str
    data_sources: DataSources
    company_name: str
    facilities: list[Facility]
    vehicles: list[Vehicle]
    products: list[Product]
    materials: list[Material]
    inventory: list[Inventory]
    orders: list[Order]
