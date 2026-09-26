from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Query, Request, status

from app.errors import ApiError
from app.inventory.dashboard import summary as dashboard_summary
from app.inventory.db import connect
from app.inventory.forecast import product_forecast
from app.inventory.operations import (
    adjust_stock,
    create_transaction,
    get_transaction,
    list_movements,
    list_products,
    list_transactions,
    stock_in,
    void_transaction,
)
from app.inventory.procurement import decide, recommendations
from app.inventory.risk import evaluate_risks, inventory_view, public_risks
from app.inventory.schemas import (
    AdjustmentRequest,
    AdjustmentResponse,
    CreateTransactionRequest,
    DashboardSummaryResponse,
    InventoryResponse,
    InventoryRisksResponse,
    MovementListResponse,
    MovementType,
    ProcurementResponse,
    ProductForecastResponse,
    ProductsResponse,
    RecommendationDecisionRequest,
    RecommendationDecisionResponse,
    StockInRequest,
    StockInResponse,
    TransactionListResponse,
    TransactionResponse,
    VoidTransactionRequest,
)

router = APIRouter(tags=["inventory-product-track"])


def _correlation_id(value: str | None) -> str:
    return value.strip()[:120] if value and value.strip() else str(uuid4())


@router.get("/api/products", response_model=ProductsResponse)
def products(request: Request) -> dict:
    with connect(request.app.state.settings) as connection:
        return list_products(connection)


@router.post("/api/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def checkout(
    payload: CreateTransactionRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=200),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID", max_length=200),
) -> dict:
    with connect(request.app.state.settings) as connection:
        _, response = create_transaction(
            connection,
            payload,
            idempotency_key=idempotency_key,
            correlation_id=_correlation_id(correlation_id),
        )
        return response


@router.get("/api/transactions", response_model=TransactionListResponse)
def transactions(
    request: Request,
    search: str | None = Query(default=None, max_length=120),
    date_filter: Annotated[date | None, Query(alias="date")] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> dict:
    with connect(request.app.state.settings) as connection:
        return list_transactions(
            connection,
            search=search,
            business_day=date_filter,
            page=page,
            page_size=page_size,
        )


@router.get("/api/transactions/{transaction_id}", response_model=TransactionResponse)
def transaction_detail(transaction_id: UUID, request: Request) -> dict:
    with connect(request.app.state.settings) as connection:
        return get_transaction(connection, transaction_id)


@router.post("/api/transactions/{transaction_id}/void", response_model=TransactionResponse)
def void_sale(
    transaction_id: UUID,
    payload: VoidTransactionRequest,
    request: Request,
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID", max_length=200),
) -> dict:
    with connect(request.app.state.settings) as connection:
        return void_transaction(
            connection,
            transaction_id,
            payload.reason,
            correlation_id=_correlation_id(correlation_id),
        )


@router.get("/api/inventory/movements", response_model=MovementListResponse)
def movements(
    request: Request,
    ingredient_id: str | None = Query(default=None, alias="ingredientId"),
    movement_type: Annotated[MovementType | None, Query(alias="type")] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> dict:
    with connect(request.app.state.settings) as connection:
        return list_movements(
            connection,
            ingredient_id=ingredient_id,
            movement_type=movement_type,
            page=page,
            page_size=page_size,
        )


@router.get("/api/inventory", response_model=InventoryResponse)
def inventory(
    request: Request,
    search: str | None = Query(default=None, max_length=120),
    risk_level: str | None = Query(default=None, alias="riskLevel", pattern="^(LOW|MEDIUM|HIGH|STOCKOUT)$"),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID", max_length=200),
) -> dict:
    with connect(request.app.state.settings) as connection:
        return inventory_view(
            connection,
            request.app.state.settings,
            correlation_id=_correlation_id(correlation_id),
            search=search,
            risk_level=risk_level,
        )


@router.get("/api/inventory/risks", response_model=InventoryRisksResponse)
def inventory_risks(
    request: Request,
    level: str | None = Query(default=None, pattern="^(LOW|MEDIUM|HIGH|STOCKOUT)$"),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID", max_length=200),
) -> dict:
    with connect(request.app.state.settings) as connection:
        result = evaluate_risks(
            connection,
            request.app.state.settings,
            correlation_id=_correlation_id(correlation_id),
        )
        return public_risks(result, level)


@router.get("/api/forecasts/products/{product_id}", response_model=ProductForecastResponse)
def forecast_product(
    product_id: str,
    request: Request,
    horizon_days: int = Query(default=3, alias="horizonDays"),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID", max_length=200),
) -> dict:
    if horizon_days != 3:
        raise ApiError(422, "UNSUPPORTED_FORECAST_HORIZON", "Horizon forecast yang didukung adalah 3 hari.")
    with connect(request.app.state.settings) as connection:
        return product_forecast(
            connection,
            request.app.state.settings,
            product_id,
            correlation_id=_correlation_id(correlation_id),
        )


@router.post("/api/inventory/{ingredient_id}/adjustments", response_model=AdjustmentResponse)
def adjustment(
    ingredient_id: str,
    payload: AdjustmentRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=200),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID", max_length=200),
) -> dict:
    with connect(request.app.state.settings) as connection:
        _, response = adjust_stock(
            connection,
            ingredient_id,
            payload,
            idempotency_key=idempotency_key,
            correlation_id=_correlation_id(correlation_id),
        )
        return response


@router.post("/api/inventory/{ingredient_id}/stock-in", response_model=StockInResponse)
def receive_stock(
    ingredient_id: str,
    payload: StockInRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=200),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID", max_length=200),
) -> dict:
    with connect(request.app.state.settings) as connection:
        _, response = stock_in(
            connection,
            ingredient_id,
            payload,
            idempotency_key=idempotency_key,
            correlation_id=_correlation_id(correlation_id),
        )
        return response


@router.get("/api/procurement/recommendations", response_model=ProcurementResponse)
def procurement_recommendations(
    request: Request,
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID", max_length=200),
) -> dict:
    with connect(request.app.state.settings) as connection:
        return recommendations(
            connection,
            request.app.state.settings,
            correlation_id=_correlation_id(correlation_id),
        )


@router.post(
    "/api/procurement/recommendations/{recommendation_id}/decision",
    response_model=RecommendationDecisionResponse,
)
def recommendation_decision(
    recommendation_id: UUID,
    payload: RecommendationDecisionRequest,
    request: Request,
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID", max_length=200),
) -> dict:
    with connect(request.app.state.settings) as connection:
        return decide(
            connection,
            recommendation_id,
            payload.decision,
            correlation_id=_correlation_id(correlation_id),
        )


@router.get("/api/dashboard/summary", response_model=DashboardSummaryResponse)
def dashboard(
    request: Request,
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID", max_length=200),
) -> dict:
    with connect(request.app.state.settings) as connection:
        return dashboard_summary(
            connection,
            request.app.state.settings,
            correlation_id=_correlation_id(correlation_id),
        )
