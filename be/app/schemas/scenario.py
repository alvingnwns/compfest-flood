from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel, PointGeometry


class FacilityKind(StrEnum):
    SUPPLIER = "supplier"
    FACTORY = "factory"
    WAREHOUSE = "warehouse"
    STORE = "store"


class DataSourceMode(StrEnum):
    HISTORICAL_SNAPSHOT = "historical_snapshot"
    LIVE = "live"
    HYBRID = "hybrid"


class HistoricalDataStatus(StrEnum):
    AVAILABLE = "available"
    OFFLINE_SNAPSHOT = "offline_snapshot"
    UNAVAILABLE = "unavailable"


class OperationalDataStatus(StrEnum):
    SIMULATED = "simulated"
    LIVE = "live"


class Facility(APIModel):
    id: str
    name: str
    kind: FacilityKind
    location: PointGeometry


class Vehicle(APIModel):
    id: str
    label: str
    capacity_units: int = Field(gt=0)


class Product(APIModel):
    id: str
    name: str
    unit: str


class Material(APIModel):
    id: str
    name: str
    supplier_id: str
    product_ids: list[str] = Field(min_length=1)


class Inventory(APIModel):
    facility_id: str
    product_id: str
    quantity: float = Field(ge=0)
    unit: str


class Order(APIModel):
    id: str
    store_id: str
    product_id: str
    quantity: int = Field(gt=0)
    priority: Literal["normal", "high", "critical"]


class DataSources(APIModel):
    mode: DataSourceMode
    historical_status: HistoricalDataStatus
    operational_status: OperationalDataStatus
    historical_provider: str
    snapshot_id: str | None = None


class Scenario(APIModel):
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
