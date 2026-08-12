from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.health import router as health_router
from app.api.map import router as map_router
from app.api.scenarios import router as scenarios_router
from app.api.simulations import router as simulations_router
from app.core.config import Settings, get_settings
from app.errors import (
    ApiError,
    api_error_handler,
    http_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.services.flood_risk_service import warm_model
from app.services.routing_service import warm_graphs


@asynccontextmanager
async def lifespan(_: FastAPI):
    warm_model()
    warm_graphs()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings or get_settings()
    application = FastAPI(
        title="ResiliChain AI API",
        version="0.2.0",
        description=(
            "Offline-first historical flood-risk replay with simulated business inputs and connected computation."
        ),
        lifespan=lifespan,
    )
    application.state.settings = configured
    application.add_middleware(
        CORSMiddleware,
        allow_origins=configured.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )
    application.add_exception_handler(ApiError, api_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_error_handler)
    application.add_exception_handler(Exception, unhandled_error_handler)
    application.include_router(health_router)
    application.include_router(map_router)
    application.include_router(scenarios_router)
    application.include_router(simulations_router)

    return application


def run() -> None:
    import uvicorn

    configured = get_settings()
    uvicorn.run("app.main:app", host=configured.host, port=configured.port)


app = create_app()
