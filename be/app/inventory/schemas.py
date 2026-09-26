from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import ApiModel

InventoryUnit = Literal["g", "kg", "ml", "l", "pcs"]
TransactionSource = Literal["POS_SIMULATOR", "POS_CASHIER", "IMPORT"]
MovementType = Literal["SALE", "STOCK_IN", "ADJUSTMENT", "WASTE", "DAMAGE"]
AdjustmentReason = Literal["PHYSICAL_COUNT", "WASTE", "DAMAGE", "OTHER"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "STOCKOUT"]
RecommendationStatus = Literal["PENDING", "APPROVED", "REJECTED"]
RecommendationDecision = Literal["APPROVED", "REJECTED"]
OptimizerStatus = Literal["OPTIMAL", "FEASIBLE", "INFEASIBLE", "ERROR"]
PlanOutcome = Literal["COMPLETE", "PARTIAL", "INFEASIBLE"]
ExplanationSource = Literal["QWEN", "FALLBACK"]


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value


class Product(ApiModel):
    id: str
    name: str
    price: int = Field(ge=0)
    currency: Literal["IDR"] = "IDR"
    is_active: bool


class ProductsResponse(ApiModel):
    products: list[Product]


class TransactionItemRequest(ApiModel):
    product_id: str
    quantity: int = Field(gt=0, le=1_000_000)


class CreateTransactionRequest(ApiModel):
    source: TransactionSource
    items: list[TransactionItemRequest] = Field(min_length=1)


class TransactionItem(ApiModel):
    product_id: str
    product_name: str
    quantity: int = Field(gt=0)
    unit_price: int = Field(ge=0)
    subtotal: int = Field(ge=0)


class IngredientQuantity(ApiModel):
    ingredient_id: str
    ingredient_name: str
    quantity: float
    unit: InventoryUnit


class Transaction(ApiModel):
    id: str
    created_at: datetime
    source: TransactionSource
    currency: Literal["IDR"] = "IDR"
    total_amount: int = Field(ge=0)
    total_items: int = Field(gt=0)
    items: list[TransactionItem]
    ingredient_consumption: list[IngredientQuantity]

    _created_at_aware = field_validator("created_at")(_aware)


class TransactionResponse(ApiModel):
    transaction: Transaction


class VoidTransactionRequest(ApiModel):
    reason: str = Field(min_length=3, max_length=500)


class TransactionSummary(ApiModel):
    id: str
    created_at: datetime
    source: TransactionSource
    total_items: int = Field(gt=0)
    total_amount: int = Field(ge=0)
    currency: Literal["IDR"] = "IDR"

    _created_at_aware = field_validator("created_at")(_aware)


class Pagination(ApiModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class TransactionListResponse(ApiModel):
    items: list[TransactionSummary]
    pagination: Pagination


class InventoryItem(ApiModel):
    ingredient_id: str
    ingredient_name: str
    category: str | None
    current_stock: float = Field(ge=0)
    unit: InventoryUnit
    predicted_requirement: float = Field(ge=0)
    requirement_horizon_days: Literal[3] = 3
    risk_level: RiskLevel
    risk_reason: str
    updated_at: datetime

    _updated_at_aware = field_validator("updated_at")(_aware)


class InventoryResponse(ApiModel):
    items: list[InventoryItem]


class InventoryMovement(ApiModel):
    id: str
    ingredient_id: str
    ingredient_name: str
    type: MovementType
    quantity_change: float
    unit: InventoryUnit
    transaction_id: str | None
    note: str | None
    created_at: datetime

    _created_at_aware = field_validator("created_at")(_aware)


class MovementListResponse(ApiModel):
    items: list[InventoryMovement]
    pagination: Pagination


class AdjustmentRequest(ApiModel):
    counted_stock: float = Field(ge=0)
    unit: InventoryUnit
    reason: AdjustmentReason
    note: str | None = Field(default=None, max_length=500)
    expected_inventory_version: int | None = Field(default=None, ge=0)


class InventorySnapshot(ApiModel):
    ingredient_id: str
    ingredient_name: str
    current_stock: float = Field(ge=0)
    unit: InventoryUnit
    updated_at: datetime

    _updated_at_aware = field_validator("updated_at")(_aware)


class AdjustmentMovement(ApiModel):
    id: str
    type: MovementType
    quantity_change: float
    unit: InventoryUnit
    created_at: datetime

    _created_at_aware = field_validator("created_at")(_aware)


class AdjustmentResponse(ApiModel):
    inventory: InventorySnapshot
    movement: AdjustmentMovement | None


class StockInRequest(ApiModel):
    quantity: float = Field(gt=0)
    unit: InventoryUnit
    supplier_id: str
    note: str | None = Field(default=None, max_length=500)
    recommendation_id: str | None = None
    external_receipt_id: str | None = Field(default=None, min_length=1, max_length=120)


class StockInResponse(ApiModel):
    inventory: InventorySnapshot
    movement_id: str


class DemandHistoryPoint(ApiModel):
    date: date
    actual_demand: int = Field(ge=0)
    history_source: Literal["SYNTHETIC_DEMAND", "OBSERVED_SALES"] | None = None


class ForecastPoint(ApiModel):
    date: date
    horizon: Literal[1, 2, 3]
    predicted_demand: int = Field(ge=0)


class ForecastModel(ApiModel):
    name: str
    version: str


class ForecastProduct(ApiModel):
    id: str
    name: str


class IngredientRequirement(ApiModel):
    ingredient_id: str
    ingredient_name: str
    total_required: float = Field(ge=0)
    unit: InventoryUnit


class ProductForecastResponse(ApiModel):
    product: ForecastProduct
    horizon_days: Literal[3] = 3
    generated_at: datetime
    model: ForecastModel
    history: list[DemandHistoryPoint]
    forecast: list[ForecastPoint]
    ingredient_requirements: list[IngredientRequirement]
    forecast_run_id: str | None = None
    as_of_date: date | None = None
    data_cutoff: datetime | None = None
    source: Literal["XGBOOST", "FALLBACK"] | None = None
    is_synthetic: bool | None = None
    fallback_reason: str | None = None

    _generated_at_aware = field_validator("generated_at")(_aware)


class DailyProjection(ApiModel):
    date: date
    requirement: float = Field(ge=0)
    incoming_quantity: float = Field(ge=0)
    projected_stock: float


class InventoryRisk(ApiModel):
    ingredient_id: str
    ingredient_name: str
    unit: InventoryUnit
    current_stock: float = Field(ge=0)
    incoming_stock: float = Field(ge=0)
    predicted_requirement: float = Field(ge=0)
    projected_stock: float
    safety_stock: float = Field(ge=0)
    reorder_point: float = Field(ge=0)
    lead_time_hours: int = Field(ge=0)
    risk_level: RiskLevel
    risk_reason: str
    reason_codes: list[str] = Field(default_factory=list)
    projected_stockout_date: date | None = None
    inventory_version: str | None = None
    forecast_run_id: str | None = None
    daily_projection: list[DailyProjection] = Field(default_factory=list)


class InventoryRisksResponse(ApiModel):
    generated_at: datetime
    horizon_days: Literal[3] = 3
    items: list[InventoryRisk]

    _generated_at_aware = field_validator("generated_at")(_aware)


class SupplierSummary(ApiModel):
    id: str
    name: str
    lead_time_hours: int = Field(ge=0)


class RecommendationExplanation(ApiModel):
    text: str
    source: ExplanationSource


class ProcurementRecommendation(ApiModel):
    id: str
    ingredient_id: str
    ingredient_name: str
    unit: InventoryUnit
    current_stock: float = Field(ge=0)
    predicted_requirement: float = Field(ge=0)
    safety_stock: float = Field(ge=0)
    projected_stock: float
    risk_level: RiskLevel
    recommended_order_quantity: float = Field(gt=0)
    recommended_order_at: date
    supplier: SupplierSummary
    status: RecommendationStatus
    explanation: RecommendationExplanation
    expected_arrival_at: datetime | None = None
    estimated_cost: int | None = Field(default=None, ge=0)
    reason_codes: list[str] = Field(default_factory=list)
    unmet_quantity: float | None = Field(default=None, ge=0)


class ProcurementResponse(ApiModel):
    generated_at: datetime
    optimizer_status: OptimizerStatus
    recommendations: list[ProcurementRecommendation]
    plan_id: str | None = None
    inventory_version: str | None = None
    forecast_run_id: str | None = None
    is_stale: bool | None = None
    plan_outcome: PlanOutcome | None = None
    solver_status_detail: str | None = None
    total_estimated_cost: int | None = Field(default=None, ge=0)
    currency: Literal["IDR"] | None = None
    limitations: list[str] = Field(default_factory=list)

    _generated_at_aware = field_validator("generated_at")(_aware)


class RecommendationDecisionRequest(ApiModel):
    decision: RecommendationDecision


class RecommendationDecisionResponse(ApiModel):
    id: str
    status: RecommendationStatus
    reviewed_at: datetime

    _reviewed_at_aware = field_validator("reviewed_at")(_aware)


class DashboardToday(ApiModel):
    revenue: int = Field(ge=0)
    currency: Literal["IDR"] = "IDR"
    transactions: int = Field(ge=0)
    products_sold: int = Field(ge=0)


class DashboardInventory(ApiModel):
    at_risk_ingredient_count: int = Field(ge=0)
    active_recommendation_count: int = Field(ge=0)


class PriorityAction(ApiModel):
    recommendation_id: str
    ingredient_id: str
    ingredient_name: str
    risk_level: RiskLevel
    recommended_order_quantity: float = Field(gt=0)
    unit: InventoryUnit
    recommended_order_at: date
    summary: str


class DashboardSummaryResponse(ApiModel):
    generated_at: datetime
    today: DashboardToday
    inventory: DashboardInventory
    priority_actions: list[PriorityAction]

    _generated_at_aware = field_validator("generated_at")(_aware)


class QwenRecommendationExplanation(ApiModel):
    recommendation_id: str
    text: str = Field(min_length=1, max_length=1000)


class QwenExplanationOutput(ApiModel):
    summary: str = Field(min_length=1, max_length=1500)
    recommendation_explanations: list[QwenRecommendationExplanation]


class QwenProviderExplanation(ApiModel):
    recommendation_id: str
    explanation: str = Field(min_length=1, max_length=1000)


class QwenProviderOutput(ApiModel):
    explanations: list[QwenProviderExplanation]


class ExplanationRecommendationContext(ApiModel):
    recommendation_id: str
    ingredient_id: str
    ingredient_name: str
    unit: InventoryUnit
    current_stock: float
    predicted_requirement: float
    safety_stock: float
    projected_stock: float
    risk_level: RiskLevel
    recommended_order_quantity: float
    supplier_id: str
    supplier_name: str
    lead_time_hours: int
    expected_arrival_at: datetime | None
    estimated_cost: int | None
    unmet_quantity: float | None
    reason_codes: list[str]


class InventoryExplanationContext(ApiModel):
    plan_id: str
    inventory_version: str
    forecast_run_id: str
    optimizer_status: OptimizerStatus
    plan_outcome: PlanOutcome
    total_estimated_cost: int
    currency: Literal["IDR"]
    limitations: list[str]
    recommendations: list[ExplanationRecommendationContext]
