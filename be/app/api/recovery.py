from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.container import Container, get_container
from app.schemas.recovery import RecoveryGenerationRequest, RecoveryPlan

router = APIRouter(prefix="/simulations/{simulation_id}/recovery", tags=["recovery"])
ContainerDependency = Annotated[Container, Depends(get_container)]


@router.post("", response_model=RecoveryPlan, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def create_recovery(
    simulation_id: str, payload: RecoveryGenerationRequest, container: ContainerDependency
) -> RecoveryPlan:
    return container.recovery.create(simulation_id, payload.constraints)


@router.get("", response_model=RecoveryPlan, response_model_exclude_none=True)
async def get_recovery(simulation_id: str, container: ContainerDependency) -> RecoveryPlan:
    return container.recovery.get(simulation_id)
