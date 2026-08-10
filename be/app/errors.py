from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details


def error_body(
    code: str, message: str, *, retryable: bool = False, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message, "retryable": retryable}
    if details is not None:
        body["details"] = details
    return body


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, retryable=exc.retryable, details=exc.details),
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    syntactic_error_types = {"json_invalid", "missing"}
    status_code = 400 if any(error["type"] in syntactic_error_types for error in errors) else 422
    code = "invalid_request" if status_code == 400 else "validation_error"
    message = "Request syntax is invalid." if status_code == 400 else "The request is semantically invalid."
    return JSONResponse(
        status_code=status_code,
        content=error_body(code, message, details={"errors": errors}),
    )


async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 404:
        return JSONResponse(status_code=404, content=error_body("not_found", "Resource not found."))

    return JSONResponse(
        status_code=exc.status_code,
        content=error_body("http_error", "The request could not be completed."),
    )


async def unhandled_error_handler(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_body("internal_error", "An unexpected server error occurred.", retryable=True),
    )
