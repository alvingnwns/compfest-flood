from app.schemas.disruption import DisruptionAnalysis
from app.schemas.impact import ActionCounts, ImpactComparison, KpiMetric
from app.schemas.recovery import RecoveryResult
from app.schemas.scenario import Scenario


def calculate_kpi(
    simulation_id: str, scenario: Scenario, disruption: DisruptionAnalysis, recovery: RecoveryResult
) -> ImpactComparison:
    
    total_orders = len(scenario.orders)
    
    # Baseline calculations
    baseline_fulfilled = total_orders - len(disruption.impact.impacted_order_ids)
    baseline_failed = total_orders - baseline_fulfilled
    
    baseline_sales_exposure = disruption.impact.sales_exposure.amount
    
    # This is a naive estimation for demonstration
    baseline_otd = baseline_fulfilled / total_orders if total_orders > 0 else 0
    baseline_avg_delay = 120 if baseline_failed > 0 else 0
    
    # Recovery calculations
    if recovery.summary:
        recovery_fulfilled = recovery.summary.recoverable_orders
    else:
        recovery_fulfilled = total_orders
        
    recovery_failed = total_orders - recovery_fulfilled
    recovery_otd = recovery_fulfilled / total_orders if total_orders > 0 else 0
    recovery_avg_delay = 45 if recovery_failed > 0 else 0
    
    # Rough estimate of mitigated exposure
    mitigated_ratio = 1.0
    if baseline_failed > 0:
        mitigated_ratio = (baseline_failed - recovery_failed) / baseline_failed
        if mitigated_ratio < 0:
            mitigated_ratio = 0
            
    recovery_sales_exposure = baseline_sales_exposure * (1 - mitigated_ratio)

    mfg_count = len(recovery.manufacturing_actions) if recovery.manufacturing_actions else 0
    log_count = len(recovery.logistics_actions) if recovery.logistics_actions else 0
    com_count = len(recovery.commerce_actions) if recovery.commerce_actions else 0

    return ImpactComparison(
        simulation_id=simulation_id,
        metrics=[
            KpiMetric(key="orders-fulfilled", baseline=baseline_fulfilled, recovery=recovery_fulfilled, total=total_orders),
            KpiMetric(key="on-time-delivery", baseline=baseline_otd, recovery=recovery_otd),
            KpiMetric(key="failed-orders", baseline=baseline_failed, recovery=recovery_failed),
            KpiMetric(key="average-delay", baseline=baseline_avg_delay, recovery=recovery_avg_delay),
            KpiMetric(key="sales-exposure-risk", baseline=baseline_sales_exposure, recovery=recovery_sales_exposure, currency="IDR"),
        ],
        action_counts=ActionCounts(
            manufacturing=mfg_count,
            logistics=log_count,
            commerce=com_count
        )
    )
