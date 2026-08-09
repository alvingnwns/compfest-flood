from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.container import Container, get_container
from app.schemas.scenario import Scenario

router = APIRouter(prefix="/scenarios", tags=["scenarios"])
ContainerDependency = Annotated[Container, Depends(get_container)]


@router.get("/historical-jakarta", response_model=Scenario, response_model_exclude_none=True)
async def get_historical_jakarta(container: ContainerDependency) -> Scenario:
    return container.scenarios.get_historical_jakarta()
