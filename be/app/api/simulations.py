from __future__ import annotations

import json

from fastapi import APIRouter, status

from app.errors import ApiError
from app.repositories.scenario_repository import get_historical_jakarta
from app.repositories.simulation_repository import simulation_repository
from app.schemas.disruption import DisruptionAnalysis
from app.schemas.impact import ImpactComparison
from app.schemas.recovery import RecoveryRequest, RecoveryResult
from app.schemas.simulation import RunSimulationRequest, Simulation
from app.services.kpi_service import calculate_kpi
from app.services.recovery_service import generate_recovery_plan
from app.services.simulation_service import create_simulation, get_simulation

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post("", response_model=Simulation, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
def run_simulation(request: RunSimulationRequest) -> Simulation:
    return create_simulation(request)


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
            details={"status": simulation.status},
        )
    disruption = simulation_repository.get_disruption(simulation_id)
    if disruption is None:
        raise ApiError(409, "disruption_not_ready", "Disruption analysis is not ready.")
    return disruption


@router.post(
    "/{simulation_id}/recovery",
    response_model=RecoveryResult,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create_recovery_plan(simulation_id: str, request: RecoveryRequest | None = None) -> RecoveryResult:
    simulation = get_simulation(simulation_id)
    if simulation.status != "completed":
        raise ApiError(409, "simulation_not_ready", "Simulation is not completed yet.")
    fingerprint = json.dumps(request.model_dump(mode="json") if request else {}, sort_keys=True)
    existing = simulation_repository.get_recovery(simulation_id, fingerprint)
    if existing is not None:
        return existing
    disruption = simulation_repository.get_disruption(simulation_id)
    if disruption is None:
        raise ApiError(409, "disruption_not_ready", "Disruption analysis is not ready.")
    scenario = simulation_repository.get_effective_scenario(simulation_id) or get_historical_jakarta()
    recovery = generate_recovery_plan(
        simulation_id,
        scenario,
        disruption,
        request.constraints if request else None,
    )
    simulation_repository.save_recovery(simulation_id, fingerprint, recovery)
    simulation_repository.save_impact(
        simulation_id,
        calculate_kpi(
            simulation_id,
            scenario,
            recovery,
            business_data_source=simulation.business_data_source,
        ),
    )
    return recovery


@router.get("/{simulation_id}/recovery", response_model=RecoveryResult, response_model_exclude_none=True)
def get_recovery_plan(simulation_id: str) -> RecoveryResult:
    get_simulation(simulation_id)
    recovery = simulation_repository.get_recovery(simulation_id)
    if recovery is None:
        raise ApiError(409, "recovery_not_ready", "Recovery plan has not been generated.")
    return recovery


@router.get("/{simulation_id}/impact", response_model=ImpactComparison, response_model_exclude_none=True)
def get_impact_comparison(simulation_id: str) -> ImpactComparison:
    get_simulation(simulation_id)
    impact = simulation_repository.get_impact(simulation_id)
    if impact is None:
        raise ApiError(409, "recovery_not_ready", "Impact is unavailable until recovery is generated.")
    return impact
