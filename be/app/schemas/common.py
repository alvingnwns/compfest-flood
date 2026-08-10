from __future__ import annotations

from typing import Any

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
