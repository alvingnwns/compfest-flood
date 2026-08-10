from fastapi import APIRouter, status

from app.errors import ApiError
from app.schemas.simulation import RunSimulationRequest, Simulation
from app.schemas.disruption import DisruptionAnalysis
from app.repositories.simulation_repository import simulation_repository
from app.services.simulation_service import create_simulation, get_simulation

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post("", response_model=Simulation, status_code=status.HTTP_201_CREATED)
def run_simulation(request: RunSimulationRequest) -> Simulation:
    return create_simulation(request.scenario_id)


@router.get("/{simulation_id}", response_model=Simulation)
def get_simulation_status(simulation_id: str) -> Simulation:
    return get_simulation(simulation_id)


@router.get("/{simulation_id}/disruption", response_model=DisruptionAnalysis)
def get_simulation_disruption(simulation_id: str) -> DisruptionAnalysis:
    simulation = get_simulation(simulation_id)
    if simulation.status != "completed":
        raise ApiError(
            409,
            "simulation_not_ready",
            "Simulation is not completed yet.",
            details={"status": simulation.status}
        )
        
    disruption = simulation_repository.get_disruption(simulation_id)
    if not disruption:
        raise ApiError(
            404,
            "disruption_not_found",
            "Disruption analysis not found for this simulation."
        )
    return disruption
