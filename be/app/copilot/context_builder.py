from __future__ import annotations

from app.errors import ApiError
from app.repositories.scenario_repository import get_historical_jakarta
from app.repositories.simulation_repository import simulation_repository
from app.schemas.disruption import RoadRisk
from app.services.simulation_service import get_simulation

from .schemas import (
    CopilotContext,
    HazardContext,
    IssueContext,
    KpiContext,
    RecoveryActionContext,
    RoadContext,
    RouteContext,
)

MAX_ROADS = 12
MAX_ACTIONS_PER_CATEGORY = 12


def _road_score(road: RoadRisk) -> float:
    return road.dynamic_road_risk_score if road.dynamic_road_risk_score is not None else road.risk_probability


def build_copilot_context(simulation_id: str) -> CopilotContext:
    simulation = get_simulation(simulation_id)
    if simulation.status != "completed":
        raise ApiError(409, "simulation_not_ready", "Simulation is not completed yet.")

    disruption = simulation_repository.get_disruption(simulation_id)
    if disruption is None:
        raise ApiError(409, "disruption_not_ready", "Disruption analysis is not ready.")

    scenario = simulation_repository.get_effective_scenario(simulation_id) or get_historical_jakarta()
    recovery = simulation_repository.get_recovery(simulation_id)
    impact = simulation_repository.get_impact(simulation_id)
    facility_names = {facility.id: facility.name for facility in scenario.facilities}

    affected_roads = [
        RoadContext(
            segment_id=road.segment_id,
            road_name=road.road_name,
            risk_level=road.risk_level,
            risk_score=_road_score(road),
            score_semantics=(
                road.dynamic_risk_score_semantics
                or "estimated historical road-corridor flood exposure; not road-closure certainty"
            ),
            affected_supplier_ids=road.affected_supplier_ids,
            affected_warehouse_ids=road.affected_warehouse_ids,
            affected_order_ids=road.affected_order_ids,
        )
        for road in sorted(disruption.roads, key=_road_score, reverse=True)[:MAX_ROADS]
    ]
    routes = [
        RouteContext(
            route_id=route.id,
            route_type=route.type,
            origin=facility_names.get(route.origin_facility_id, route.origin_facility_id),
            destination=facility_names.get(route.destination_facility_id, route.destination_facility_id),
            eta_minutes=route.eta_minutes,
            flood_exposure=route.flood_exposure,
            exposure_score=route.flood_exposure_probability,
            affected_road_segment_ids=route.affected_road_segment_ids,
        )
        for route in disruption.routes
    ]

    recovery_actions: list[RecoveryActionContext] = []
    if recovery is not None:
        action_groups = (
            ("manufacturing", recovery.manufacturing_actions or []),
            ("logistics", recovery.logistics_actions or []),
            ("commerce", recovery.commerce_actions or []),
        )
        for category, actions in action_groups:
            recovery_actions.extend(
                RecoveryActionContext(
                    category=category,
                    entity_id=getattr(action, "order_id", getattr(action, "product_id", action.id)),
                    what=action.what,
                    why=action.why,
                    expected_impact=action.expected_impact,
                )
                for action in actions[:MAX_ACTIONS_PER_CATEGORY]
            )

    hazard = None
    if simulation.hazard is not None:
        hazard = HazardContext(
            rainfall_scenario=simulation.hazard.rainfall_scenario,
            relative_hazard_index=simulation.hazard.relative_hazard_index,
            temporal_hazard_score=simulation.hazard.temporal_hazard_score,
            probability_calibrated=simulation.hazard.probability_calibrated,
            semantics=(
                "what-if relative hazard from a historical-derived rainfall pattern; "
                "not live weather or a calibrated flood forecast"
            ),
        )

    return CopilotContext(
        simulation_id=simulation.id,
        scenario_id=simulation.scenario_id,
        scenario_name=scenario.name,
        business_data_source=simulation.business_data_source,
        analysis_mode=simulation.analysis_mode,
        region=simulation.region,
        model_version=simulation.model_version,
        optimizer_version=simulation.optimizer_version,
        hazard=hazard,
        affected_roads=affected_roads,
        routes=routes,
        impacted_suppliers=[facility_names.get(item, item) for item in disruption.impact.impacted_supplier_ids],
        impacted_warehouses=[facility_names.get(item, item) for item in disruption.impact.impacted_warehouse_ids],
        impacted_orders=disruption.impact.impacted_order_ids,
        road_segments_at_risk=disruption.impact.road_segments_at_risk,
        disruption_sales_exposure=disruption.impact.sales_exposure.amount,
        disruption_sales_exposure_currency=disruption.impact.sales_exposure.currency,
        prioritized_issues=[
            IssueContext(severity=issue.severity, subject=issue.subject, description=issue.description)
            for issue in disruption.impact.issues
        ],
        recovery_status=recovery.status if recovery is not None else None,
        recovery_summary=(
            recovery.summary.model_dump() if recovery is not None and recovery.summary is not None else None
        ),
        recovery_actions=recovery_actions,
        kpis=(
            [
                KpiContext(
                    key=metric.key,
                    baseline=metric.baseline,
                    recovery=metric.recovery,
                    total=metric.total,
                    currency=metric.currency,
                )
                for metric in impact.metrics
            ]
            if impact is not None
            else []
        ),
    )


def suggested_questions(context: CopilotContext) -> list[str]:
    questions = ["Which supplier is most affected?", "What is the biggest bottleneck?"]
    if context.routes:
        questions.append("Why was this route chosen?")
    if context.recovery_actions:
        questions.extend(["Why was this recovery plan selected?", "What trade-offs does this plan make?"])
    if context.impacted_orders:
        questions.append("Which orders remain at risk?")
    if any(metric.key == "sales-exposure-risk" for metric in context.kpis):
        questions.append("How did the recovery plan change sales exposure?")
    return questions[:6]
