from fastapi import APIRouter

from app.repositories.scenario_repository import get_historical_jakarta
from app.schemas.scenario import Scenario

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("/historical-jakarta", response_model=Scenario, response_model_exclude_none=True)
def get_historical_jakarta_scenario() -> Scenario:
    """Return the local historical-replay scenario selected by the current MVP UI."""
    return get_historical_jakarta()
