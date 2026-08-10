from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.common import APIModel


class OrdersFulfilledMetric(APIModel):
    key: Literal["orders-fulfilled"]
    baseline: int = Field(ge=0)
    recovery: int = Field(ge=0)
    total: int = Field(gt=0)


class OnTimeDeliveryMetric(APIModel):
    key: Literal["on-time-delivery"]
    baseline: float = Field(ge=0, le=1)
    recovery: float = Field(ge=0, le=1)


class FailedOrdersMetric(APIModel):
    key: Literal["failed-orders"]
    baseline: int = Field(ge=0)
    recovery: int = Field(ge=0)


class AverageDelayMetric(APIModel):
    key: Literal["average-delay"]
    baseline: float = Field(ge=0)
    recovery: float = Field(ge=0)


class SalesExposureMetric(APIModel):
    key: Literal["sales-exposure-risk"]
    baseline: float = Field(ge=0)
    recovery: float = Field(ge=0)
    currency: Literal["IDR"] = "IDR"


ImpactMetric = Annotated[
    OrdersFulfilledMetric | OnTimeDeliveryMetric | FailedOrdersMetric | AverageDelayMetric | SalesExposureMetric,
    Field(discriminator="key"),
]


class ActionCounts(APIModel):
    manufacturing: int = Field(ge=0)
    logistics: int = Field(ge=0)
    commerce: int = Field(ge=0)


class ImpactComparison(APIModel):
    simulation_id: str
    metrics: list[ImpactMetric] = Field(min_length=5, max_length=5)
    action_counts: ActionCounts

    @model_validator(mode="after")
    def require_unique_metric_keys(self) -> "ImpactComparison":
        if len({metric.key for metric in self.metrics}) != len(self.metrics):
            raise ValueError("Impact metric keys must be unique")
        return self
