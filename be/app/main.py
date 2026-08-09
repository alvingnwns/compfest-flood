from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import DomainError
from app.dependencies.container import build_container
from app.schemas.common import ErrorResponse


def error_response(status_code: int, error: ErrorResponse) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content=error.model_dump(mode="json", by_alias=True, exclude_none=True)
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    application = FastAPI(title="ResiliChain API", version="1.0.0")
    application.state.container = build_container(resolved_settings)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[resolved_settings.frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )

    @application.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return error_response(
            exc.status_code,
            ErrorResponse(code=exc.code, message=exc.message, retryable=exc.retryable, details=exc.details),
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors: list[dict[str, Any]] = [
            {"location": list(error["loc"]), "message": error["msg"], "type": error["type"]} for error in exc.errors()
        ]
        return error_response(
            422,
            ErrorResponse(
                code="validation_error", message="The request is invalid.", retryable=False, details={"errors": errors}
            ),
        )

    @application.exception_handler(HTTPException)
    async def handle_http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(
            exc.status_code,
            ErrorResponse(code="http_error", message=str(exc.detail), retryable=exc.status_code >= 500),
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
        return error_response(
            500,
            ErrorResponse(code="internal_server_error", message="An unexpected server error occurred.", retryable=True),
        )

    @application.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "engineMode": resolved_settings.engine_mode}

    application.include_router(api_router)
    return application


app = create_app()
