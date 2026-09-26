from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


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


_INVENTORY_API_PREFIXES = (
    "/api/products",
    "/api/transactions",
    "/api/inventory",
    "/api/forecasts",
    "/api/procurement",
    "/api/dashboard",
)


def _uses_inventory_error_contract(request: Request) -> bool:
    return request.url.path.startswith(_INVENTORY_API_PREFIXES)


def inventory_error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    if _uses_inventory_error_contract(request):
        return JSONResponse(
            status_code=exc.status_code,
            content=inventory_error_body(exc.code, exc.message, exc.details),
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, retryable=exc.retryable, details=exc.details),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [_json_safe(error) for error in exc.errors()]
    syntactic_error_types = {"json_invalid", "missing"}
    status_code = 400 if any(error["type"] in syntactic_error_types for error in errors) else 422
    code = "invalid_request" if status_code == 400 else "validation_error"
    message = "Sintaks permintaan tidak valid." if status_code == 400 else "Isi permintaan tidak valid."
    if _uses_inventory_error_contract(request):
        return JSONResponse(
            status_code=status_code,
            content=inventory_error_body(
                "INVALID_REQUEST" if status_code == 400 else "VALIDATION_ERROR",
                message,
                {"errors": errors},
            ),
        )
    return JSONResponse(
        status_code=status_code,
        content=error_body(code, message, details={"errors": errors}),
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return "<binary input omitted>"
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if _uses_inventory_error_contract(request):
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        message = "Sumber daya tidak ditemukan." if exc.status_code == 404 else "Permintaan tidak dapat diselesaikan."
        return JSONResponse(status_code=exc.status_code, content=inventory_error_body(code, message))
    if exc.status_code == 404:
        return JSONResponse(status_code=404, content=error_body("not_found", "Sumber daya tidak ditemukan."))

    return JSONResponse(
        status_code=exc.status_code,
        content=error_body("http_error", "Permintaan tidak dapat diselesaikan."),
    )


async def unhandled_error_handler(request: Request, __: Exception) -> JSONResponse:
    if _uses_inventory_error_contract(request):
        return JSONResponse(
            status_code=500,
            content=inventory_error_body("INTERNAL_ERROR", "Terjadi kesalahan server yang tidak terduga."),
        )
    return JSONResponse(
        status_code=500,
        content=error_body("internal_error", "Terjadi kesalahan server yang tidak terduga.", retryable=True),
    )
