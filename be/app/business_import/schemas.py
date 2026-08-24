from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.scenario import Inventory, Material, Order, Product


class ImportValidationIssue(ApiModel):
    sheet: str
    row: int | None = None
    column: str | None = None
    code: str
    message: str


class ProductImportRow(ApiModel):
    source_row: int = Field(exclude=True)
    product_id: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    selling_price: float = Field(ge=0)
    unit: str = Field(default="unit", min_length=1)


class OrderImportRow(ApiModel):
    source_row: int = Field(exclude=True)
    order_id: str = Field(min_length=1)
    store_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    priority: Literal["normal", "high", "critical"]
    deadline_minutes: int = Field(ge=0)


class InventoryImportRow(ApiModel):
    source_row: int = Field(exclude=True)
    warehouse_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    available_quantity: float = Field(ge=0)


class MaterialImportRow(ApiModel):
    source_row: int = Field(exclude=True)
    material_id: str = Field(min_length=1)
    material_name: str = Field(min_length=1)
    supplier_id: str = Field(min_length=1)
    available_quantity: float = Field(ge=0)


class BomImportRow(ApiModel):
    source_row: int = Field(exclude=True)
    product_id: str = Field(min_length=1)
    material_id: str = Field(min_length=1)
    quantity_required: float = Field(gt=0)


class ParsedBusinessWorkbook(ApiModel):
    products: list[ProductImportRow]
    orders: list[OrderImportRow]
    inventory: list[InventoryImportRow]
    materials: list[MaterialImportRow]
    bom: list[BomImportRow]


class BusinessSnapshotSummary(ApiModel):
    products_loaded: int
    orders_loaded: int
    inventory_rows: int
    materials_loaded: int
    bom_relationships: int
    total_order_value: float
    currency: Literal["IDR"] = "IDR"


class BusinessSnapshot(ApiModel):
    id: str
    source: Literal["custom"] = "custom"
    created_at: datetime
    expires_at: datetime
    products: list[Product]
    orders: list[Order]
    inventory: list[Inventory]
    materials: list[Material]
    summary: BusinessSnapshotSummary


class BusinessImportResponse(ApiModel):
    valid: Literal[True] = True
    business_snapshot_id: str
    business_data_source: Literal["custom"] = "custom"
    expires_at: datetime
    summary: BusinessSnapshotSummary
    products: list[Product] = Field(default_factory=list)
    inventory: list[Inventory] = Field(default_factory=list)
    errors: list[ImportValidationIssue] = Field(default_factory=list)
