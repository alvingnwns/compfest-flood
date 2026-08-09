from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.container import Container, get_container
from app.schemas.disruption import DisruptionAnalysis
from app.schemas.impact import ImpactComparison
from app.schemas.simulation import RunSimulationRequest, Simulation

router = APIRouter(prefix="/simulations", tags=["simulations"])
ContainerDependency = Annotated[Container, Depends(get_container)]


@router.post("", response_model=Simulation, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def create_simulation(payload: RunSimulationRequest, container: ContainerDependency) -> Simulation:
    return container.simulations.create(payload.scenario_id)


@router.get("/{simulation_id}", response_model=Simulation, response_model_exclude_none=True)
async def get_simulation(simulation_id: str, container: ContainerDependency) -> Simulation:
    return container.simulations.get(simulation_id)


@router.get("/{simulation_id}/disruption", response_model=DisruptionAnalysis, response_model_exclude_none=True)
async def get_disruption(simulation_id: str, container: ContainerDependency) -> DisruptionAnalysis:
    return container.disruption.get(simulation_id)


@router.get("/{simulation_id}/impact", response_model=ImpactComparison, response_model_exclude_none=True)
async def get_impact(simulation_id: str, container: ContainerDependency) -> ImpactComparison:
    return container.impact.get(simulation_id)
