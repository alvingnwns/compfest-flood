from __future__ import annotations

from app.copilot.schemas import CopilotContext, CopilotRequest


def _format_number(value: float) -> str:
    return f"{value:,.0f}"


class DeterministicCopilotProvider:
    name = "deterministic"

    def generate(self, request: CopilotRequest, context: CopilotContext) -> str:
        question = request.message.casefold()
        if any(term in question for term in ("tomorrow", "besok", "live weather", "real-time", "forecast")):
            return (
                "That information is not available in the current simulation context. "
                "Dynamic Hazard is a historical-derived what-if relative-hazard scenario, "
                "not live weather or a flood forecast."
            )
        if any(term in question for term in ("sales exposure", "paparan penjualan")):
            metric = next((item for item in context.kpis if item.key == "sales-exposure-risk"), None)
            if metric is None:
                return "Sales-exposure comparison is not available until a recovery plan and impact analysis exist."
            reduction = metric.baseline - metric.recovery
            return (
                f"Computed sales exposure changes from {_format_number(metric.baseline)} to "
                f"{_format_number(metric.recovery)} {metric.currency or ''}, a reduction of "
                f"{_format_number(reduction)}. These are already-computed scenario KPIs, not values chosen by Copilot."
            )
        if any(term in question for term in ("route", "rute")):
            action = next((item for item in context.recovery_actions if item.category == "logistics"), None)
            if action is not None:
                return f"{action.what} Reason: {action.why} Expected impact: {action.expected_impact}"
            route = next((item for item in context.routes if item.route_type == "recovery"), None)
            if route is None:
                return "A selected recovery route is not available in the current simulation context."
            return (
                f"Recovery route {route.route_id} connects {route.origin} to {route.destination}, "
                f"with computed ETA {_format_number(route.eta_minutes)} minutes and "
                f"{route.flood_exposure} estimated exposure."
            )
        if any(term in question for term in ("supplier", "pemasok")):
            if not context.impacted_suppliers:
                return "No impacted supplier is identified in the current simulation context."
            other_suppliers = (
                f" and {len(context.impacted_suppliers) - 1} other supplier(s)"
                if len(context.impacted_suppliers) > 1
                else ""
            )
            return (
                f"The impacted supplier evidence identifies {context.impacted_suppliers[0]}{other_suppliers}. "
                "The context does not support ranking beyond the recorded impacts."
            )
        if any(term in question for term in ("bottleneck", "hambatan", "kendala")):
            if not context.prioritized_issues:
                return "A bottleneck is not identified in the current simulation context."
            issue = context.prioritized_issues[0]
            return f"The highest-priority recorded issue is {issue.subject} ({issue.severity}): {issue.description}"
        if any(term in question for term in ("order", "pesanan", "priority", "prioritas")):
            if not context.impacted_orders:
                return "No impacted orders are recorded in the current simulation context."
            listed = ", ".join(context.impacted_orders[:8])
            suffix = " and additional orders" if len(context.impacted_orders) > 8 else ""
            return (
                f"Recorded impacted orders are {listed}{suffix}. Priority rationale is available only where "
                "a recovery action states it."
            )
        if any(term in question for term in ("trade-off", "tradeoff", "kompromi")):
            actions = context.recovery_actions[:3]
            if not actions:
                return "Recovery trade-offs are not available until a recovery plan exists."
            return " ".join(f"{item.what} Expected impact: {item.expected_impact}" for item in actions)
        if any(term in question for term in ("recovery plan", "rencana pemulihan", "selected", "dipilih")):
            if not context.recovery_actions:
                return "A recovery plan is not available in the current simulation context."
            action = context.recovery_actions[0]
            return f"The plan's recorded rationale begins with: {action.what} Reason: {action.why}"
        if any(term in question for term in ("dynamic hazard", "rainfall", "hujan")):
            if context.hazard is None:
                return "This simulation uses historical replay; no Dynamic Hazard scenario is active."
            return (
                f"Scenario {context.hazard.rainfall_scenario} has relative hazard index "
                f"{context.hazard.relative_hazard_index:.2f}. It is a historical-derived what-if signal, "
                "not live weather or a calibrated flood probability."
            )
        if any(term in question for term in ("joke", "capital of", "president", "weather in")):
            return "That information is not available in the current simulation context."
        return (
            f"Simulation {context.simulation_id} is a {context.analysis_mode} analysis with "
            f"{context.road_segments_at_risk} recorded road segments at risk, "
            f"{len(context.impacted_orders)} impacted orders, and recovery status "
            f"{context.recovery_status or 'not yet available'}. Ask about a recorded route, supplier, order, "
            "recovery action, or KPI."
        )
