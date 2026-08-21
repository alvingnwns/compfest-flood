from __future__ import annotations

from app.schemas.impact import ActionCounts, ImpactComparison, KpiMetric
from app.schemas.recovery import OrderOutcome, RecoveryResult
from app.schemas.scenario import Scenario


def calculate_kpi(
    simulation_id: str,
    scenario: Scenario,
    recovery: RecoveryResult,
    *,
    business_data_source: str = "demo",
) -> ImpactComparison:
    baseline = _metrics(scenario, recovery.baseline_order_outcomes)
    recovered = _metrics(scenario, recovery.recovery_order_outcomes)
    return ImpactComparison(
        simulation_id=simulation_id,
        recovery_status=recovery.status,
        business_data_source=business_data_source,
        metrics=[
            KpiMetric(
                key="orders-fulfilled",
                baseline=baseline["fulfilled"],
                recovery=recovered["fulfilled"],
                total=len(scenario.orders),
            ),
            KpiMetric(key="on-time-delivery", baseline=baseline["on_time"], recovery=recovered["on_time"]),
            KpiMetric(key="failed-orders", baseline=baseline["failed"], recovery=recovered["failed"]),
            KpiMetric(
                key="average-delay",
                baseline=baseline["average_delay"],
                recovery=recovered["average_delay"],
                baseline_observation_count=baseline["delivered"],
                recovery_observation_count=recovered["delivered"],
            ),
            KpiMetric(
                key="sales-exposure-risk",
                baseline=baseline["sales_exposure"],
                recovery=recovered["sales_exposure"],
                currency="IDR",
            ),
        ],
        action_counts=ActionCounts(
            manufacturing=len(recovery.manufacturing_actions or []),
            logistics=len(recovery.logistics_actions or []),
            commerce=len(recovery.commerce_actions or []),
        ),
    )


def _metrics(scenario: Scenario, outcomes: list[OrderOutcome]) -> dict[str, float]:
    by_order = {outcome.order_id: outcome for outcome in outcomes}
    prices = {product.id: product.unit_price for product in scenario.products}
    fulfilled = 0
    failed = 0
    on_time = 0
    delays = []
    sales_exposure = 0.0
    for order in scenario.orders:
        outcome = by_order.get(order.id)
        allocated = outcome.allocated_quantity if outcome else 0
        fulfilled += int(allocated == order.quantity)
        failed += int(allocated == 0)
        on_time += int(allocated == order.quantity and outcome is not None and outcome.delay_minutes == 0)
        if allocated > 0 and outcome:
            delays.append(outcome.delay_minutes)
        sales_exposure += (order.quantity - allocated) * prices[order.product_id]
    return {
        "fulfilled": fulfilled,
        "failed": failed,
        "on_time": on_time / len(scenario.orders) if scenario.orders else 0,
        "average_delay": round(sum(delays) / len(delays), 1) if delays else 0,
        "delivered": len(delays),
        "sales_exposure": sales_exposure,
    }
