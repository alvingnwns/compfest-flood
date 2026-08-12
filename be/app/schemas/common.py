from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base schema using the camelCase JSON convention from contract v1."""

    model_config = ConfigDict(alias_generator=lambda value: _to_camel(value), populate_by_name=True)


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ErrorResponse(ApiModel):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] | None = None


class HealthResponse(ApiModel):
    status: str = Field(description="Service availability indicator.")


class Money(ApiModel):
    amount: float = Field(ge=0)
    currency: str


RiskLevel = Literal["low", "medium", "high", "critical"]


class GeoPoint(ApiModel):
    type: Literal["Point"]
    coordinates: tuple[float, float]


class GeoLineString(ApiModel):
    type: Literal["LineString"]
    coordinates: list[tuple[float, float]]


class GeoMultiLineString(ApiModel):
    type: Literal["MultiLineString"]
    coordinates: list[list[tuple[float, float]]]


LineGeometry = GeoLineString | GeoMultiLineString


class GeoPolygon(ApiModel):
    type: Literal["Polygon"]
    coordinates: list[list[tuple[float, float]]]


class GeoMultiPolygon(ApiModel):
    type: Literal["MultiPolygon"]
    coordinates: list[list[list[tuple[float, float]]]]


PolygonalGeometry = GeoPolygon | GeoMultiPolygon
