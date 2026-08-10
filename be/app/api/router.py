from fastapi import APIRouter

from app.api.recovery import router as recovery_router
from app.api.scenarios import router as scenarios_router
from app.api.simulations import router as simulations_router

api_router = APIRouter(prefix="/api")
api_router.include_router(scenarios_router)
api_router.include_router(simulations_router)
api_router.include_router(recovery_router)
