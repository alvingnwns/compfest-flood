from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class APIModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


Position = tuple[float, float]
LineCoordinates = Annotated[list[Position], Field(min_length=2)]
LinearRing = Annotated[list[Position], Field(min_length=4)]


class PointGeometry(APIModel):
    type: Literal["Point"] = "Point"
    coordinates: Position


class LineStringGeometry(APIModel):
    type: Literal["LineString"] = "LineString"
    coordinates: LineCoordinates


class MultiLineStringGeometry(APIModel):
    type: Literal["MultiLineString"] = "MultiLineString"
    coordinates: list[LineCoordinates] = Field(min_length=1)


LineGeometry = Annotated[LineStringGeometry | MultiLineStringGeometry, Field(discriminator="type")]


class PolygonGeometry(APIModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[LinearRing] = Field(min_length=1)


class MultiPolygonGeometry(APIModel):
    type: Literal["MultiPolygon"] = "MultiPolygon"
    coordinates: list[list[LinearRing]] = Field(min_length=1)


PolygonalGeometry = Annotated[PolygonGeometry | MultiPolygonGeometry, Field(discriminator="type")]


class Money(APIModel):
    amount: float = Field(ge=0)
    currency: Literal["IDR"] = "IDR"


class ErrorResponse(APIModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool = False
    details: dict[str, Any] | None = None
