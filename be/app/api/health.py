from fastapi import APIRouter

router = APIRouter(tags=["internal"])


@router.get("/health", include_in_schema=False)
def health_check() -> dict[str, str]:
    """Internal liveness endpoint; it is intentionally outside the frontend contract."""
    return {"status": "ok", "engineMode": "connected"}
