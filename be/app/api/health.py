from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter(tags=["internal"])


@router.get("/health", response_model=HealthResponse, include_in_schema=False)
def health_check() -> HealthResponse:
    """Internal liveness endpoint; it is intentionally outside the frontend contract."""
    return HealthResponse(status="ok")
