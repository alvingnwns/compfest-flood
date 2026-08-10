from fastapi import APIRouter, status

from app.errors import ApiError
from app.schemas.simulation import RunSimulationRequest, Simulation
from app.schemas.disruption import DisruptionAnalysis
from app.repositories.scenario_repository import get_historical_jakarta
from app.repositories.simulation_repository import simulation_repository
from app.services.simulation_service import create_simulation, get_simulation
from app.services.recovery_service import generate_recovery_plan
from app.services.kpi_service import calculate_kpi
from app.schemas.recovery import RecoveryRequest, RecoveryResult
from app.schemas.impact import ImpactComparison

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post("", response_model=Simulation, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
def run_simulation(request: RunSimulationRequest) -> Simulation:
    return create_simulation(request.scenario_id)


@router.get("/{simulation_id}", response_model=Simulation, response_model_exclude_none=True)
def get_simulation_status(simulation_id: str) -> Simulation:
    return get_simulation(simulation_id)


@router.get("/{simulation_id}/disruption", response_model=DisruptionAnalysis, response_model_exclude_none=True)
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


@router.post("/{simulation_id}/recovery", response_model=RecoveryResult, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
def create_recovery_plan(simulation_id: str, request: RecoveryRequest = None) -> RecoveryResult:
    simulation = get_simulation(simulation_id)
    if simulation.status != "completed":
        raise ApiError(409, "simulation_not_ready", "Simulation is not completed yet.")
        
    disruption = simulation_repository.get_disruption(simulation_id)
    if not disruption:
        raise ApiError(404, "disruption_not_found", "Disruption analysis not found.")
        
    scenario = get_historical_jakarta()
    
    recovery = generate_recovery_plan(simulation_id, scenario, disruption, request)
    simulation_repository.save_recovery(simulation_id, recovery)
    
    impact = calculate_kpi(simulation_id, scenario, disruption, recovery)
    simulation_repository.save_impact(simulation_id, impact)
    
    return recovery


@router.get("/{simulation_id}/recovery", response_model=RecoveryResult, response_model_exclude_none=True)
def get_recovery_plan(simulation_id: str) -> RecoveryResult:
    recovery = simulation_repository.get_recovery(simulation_id)
    if not recovery:
        raise ApiError(404, "recovery_not_found", "Recovery plan not found.")
    return recovery


@router.get("/{simulation_id}/impact", response_model=ImpactComparison, response_model_exclude_none=True)
def get_impact_comparison(simulation_id: str) -> ImpactComparison:
    impact = simulation_repository.get_impact(simulation_id)
    if not impact:
        raise ApiError(404, "impact_not_found", "Impact comparison not found. Have you generated a recovery plan?")
    return impact

