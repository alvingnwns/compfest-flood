from fastapi import APIRouter, status

from app.schemas.simulation import RunSimulationRequest, Simulation
from app.services.simulation_service import create_simulation, get_simulation

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post("", response_model=Simulation, status_code=status.HTTP_201_CREATED)
def run_simulation(request: RunSimulationRequest) -> Simulation:
    return create_simulation(request.scenario_id)


@router.get("/{simulation_id}", response_model=Simulation)
def get_simulation_status(simulation_id: str) -> Simulation:
    return get_simulation(simulation_id)
