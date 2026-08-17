from __future__ import annotations

import re

from app.copilot.response_policy import classify_response_policy
from app.copilot.schemas import CopilotContext, CopilotRequest, RiskLevel, RouteContext

_INTERNAL_DETAIL_RE = re.compile(
    r"\b(?:osm-\d[\w-]*|(?:route|ord|fac|sup|wh|sim)-[a-z0-9][\w-]*|NetworkX|CP-SAT|Random Forest)\b",
    re.IGNORECASE,
)
_RISK_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _format_number(value: float) -> str:
    return f"{value:,.0f}"


def _format_currency(value: float, currency: str | None) -> str:
    if currency == "IDR":
        return f"Rp{value:,.0f}"
    return f"{_format_number(value)} {currency or ''}".strip()


def _format_minutes(value: float) -> str:
    return _format_number(value)


def _risk_label(level: RiskLevel, language: str) -> str:
    if language == "id":
        return {"low": "rendah", "medium": "sedang", "high": "tinggi", "critical": "kritis"}[level]
    return level


def _selected_recovery_route(context: CopilotContext) -> RouteContext | None:
    return next((route for route in context.routes if route.route_type == "recovery"), None)


def _matching_baseline_route(context: CopilotContext, recovery_route: RouteContext) -> RouteContext | None:
    return next(
        (
            route
            for route in context.routes
            if route.route_type == "baseline" and route.destination == recovery_route.destination
        ),
        None,
    )


def _route_tradeoff(context: CopilotContext, recovery_route: RouteContext, language: str) -> str | None:
    baseline = _matching_baseline_route(context, recovery_route)
    if baseline is None:
        return None
    eta_increase = recovery_route.eta_minutes - baseline.eta_minutes
    risk_increase = _RISK_RANK[recovery_route.flood_exposure] > _RISK_RANK[baseline.flood_exposure]
    if eta_increase > 0:
        if language == "id":
            return f"Trade-off terhitungnya adalah ETA sekitar {_format_minutes(eta_increase)} menit lebih lama."
        return f"The computed trade-off is an ETA about {_format_minutes(eta_increase)} minutes longer."
    if risk_increase:
        risk = _risk_label(recovery_route.flood_exposure, language)
        if language == "id":
            return f"Trade-off terhitungnya adalah sisa paparan rute pada tingkat {risk}."
        return f"The computed trade-off is remaining route exposure at the {risk} level."
    return None


def _safe_issue_text(value: str, fallback: str) -> str:
    return fallback if _INTERNAL_DETAIL_RE.search(value) else value


class DeterministicCopilotProvider:
    name = "deterministic"

    def generate(self, request: CopilotRequest, context: CopilotContext) -> str:
        question = request.message.casefold()
        policy = classify_response_policy(request.message)
        language = policy.language

        if policy.technical:
            technical_answer = self._technical_answer(question, context, language)
            if technical_answer is not None:
                return technical_answer

        if any(term in question for term in ("tomorrow", "besok", "live weather", "real-time", "forecast")):
            if language == "id":
                return (
                    "Simulasi ini tidak dapat menentukan kondisi besok. Dynamic Hazard adalah kondisi what-if "
                    "berbasis pola hujan historis untuk membandingkan risiko relatif, bukan cuaca langsung atau "
                    "probabilitas banjir terkalibrasi."
                )
            return (
                "This simulation cannot determine tomorrow's conditions. Dynamic Hazard is a historical-derived "
                "what-if condition for comparing relative risk, not live weather or a calibrated flood probability."
            )

        if any(term in question for term in ("sales exposure", "paparan penjualan")):
            return self._sales_exposure_answer(context, language)
        if any(term in question for term in ("route", "rute")):
            return self._route_answer(context, language)
        if any(term in question for term in ("supplier", "pemasok")):
            return self._supplier_answer(context, language)
        if any(term in question for term in ("bottleneck", "hambatan", "kendala")):
            return self._bottleneck_answer(context, language)
        if any(term in question for term in ("order", "pesanan", "priority", "prioritas")):
            return self._orders_answer(context, language)
        if any(term in question for term in ("trade-off", "tradeoff", "kompromi")):
            return self._tradeoff_answer(context, language)
        if any(term in question for term in ("recovery plan", "rencana pemulihan", "selected", "dipilih")):
            return self._recovery_answer(context, language)
        if any(term in question for term in ("dynamic hazard", "rainfall", "hujan")):
            return self._dynamic_hazard_answer(context, language)
        if any(term in question for term in ("joke", "capital of", "president", "weather in", "ibu kota")):
            return self._unavailable(language)

        if language == "id":
            return (
                f"Simulasi ini mencatat {context.road_segments_at_risk} ruas jalan berisiko dan "
                f"{len(context.impacted_orders)} pesanan terdampak. Tanyakan rute pemulihan, pemasok, pesanan, "
                "rencana pemulihan, atau KPI yang sudah dihitung."
            )
        return (
            f"This simulation records {context.road_segments_at_risk} road segments at risk and "
            f"{len(context.impacted_orders)} impacted orders. Ask about a recovery route, supplier, order, "
            "recovery plan, or computed KPI."
        )

    def _technical_answer(self, question: str, context: CopilotContext, language: str) -> str | None:
        if any(term in question for term in ("route", "rute", "osm")):
            route = _selected_recovery_route(context)
            if route is None:
                return (
                    "Detail teknis rute pemulihan tidak tersedia dalam konteks simulasi ini."
                    if language == "id"
                    else "Technical recovery-route details are not available in this simulation context."
                )
            segments = route.affected_road_segment_ids
            shown = ", ".join(segments[:6])
            remainder = max(0, len(segments) - 6)
            risk = _risk_label(route.flood_exposure, language)
            if language == "id":
                suffix = f" Sebanyak {remainder} segmen tambahan tercatat." if remainder else ""
                return (
                    f"Rute teknis {route.route_id} menghubungkan {route.origin} ke {route.destination} dengan ETA "
                    f"{_format_minutes(route.eta_minutes)} menit, paparan {risk}, dan skor paparan relatif tepat "
                    f"{route.exposure_score:.4f}. Segmen OSM yang digunakan antara lain {shown}.{suffix}"
                )
            suffix = f" {remainder} additional segments are recorded." if remainder else ""
            return (
                f"Technical route {route.route_id} connects {route.origin} to {route.destination} with an ETA of "
                f"{_format_minutes(route.eta_minutes)} minutes, {risk} exposure, and exact relative exposure "
                f"score {route.exposure_score:.4f}. OSM segments include {shown}.{suffix}"
            )
        if any(term in question for term in ("cp-sat", "constraint", "kendala solver")):
            if language == "id":
                return (
                    "Konteks mencatat hasil dan versi optimizer, tetapi tidak menyimpan daftar kendala solver yang "
                    "binding. Detail tersebut tidak tersedia dari evidence simulasi saat ini."
                )
            return (
                "The context records optimizer results and version, but it does not expose which solver constraints "
                "were binding. That detail is unavailable in the current simulation evidence."
            )
        return None

    def _sales_exposure_answer(self, context: CopilotContext, language: str) -> str:
        metric = next((item for item in context.kpis if item.key == "sales-exposure-risk"), None)
        if metric is None:
            if language == "id":
                return "Perbandingan paparan penjualan belum tersedia sebelum analisis dampak pemulihan selesai."
            return "The sales-exposure comparison is unavailable until recovery impact analysis is complete."
        reduction = metric.baseline - metric.recovery
        baseline = _format_currency(metric.baseline, metric.currency)
        recovery = _format_currency(metric.recovery, metric.currency)
        reduced = _format_currency(reduction, metric.currency)
        if language == "id":
            return (
                f"Paparan penjualan berkurang sebesar {reduced}, dari {baseline} menjadi {recovery} setelah pemulihan."
            )
        return f"Sales exposure decreases by {reduced}, from {baseline} to {recovery} after recovery."

    def _route_answer(self, context: CopilotContext, language: str) -> str:
        route = _selected_recovery_route(context)
        if route is None:
            if language == "id":
                return "Rute pemulihan terpilih belum tersedia dalam konteks simulasi saat ini."
            return "A selected recovery route is not available in the current simulation context."
        risk = _risk_label(route.flood_exposure, language)
        tradeoff = _route_tradeoff(context, route, language)
        if language == "id":
            answer = (
                f"Rute pemulihan dari {route.origin} ke {route.destination} dipilih untuk menjaga pengiriman tetap "
                "layak dalam batas kapasitas dan waktu yang tercatat. ETA rute sekitar "
                f"{_format_minutes(route.eta_minutes)} menit dengan estimasi paparan banjir {risk}."
            )
            return f"{answer} {tradeoff}" if tradeoff else answer
        answer = (
            f"The recovery route from {route.origin} to {route.destination} was selected to keep the delivery "
            "feasible within the recorded capacity and timing constraints. Its ETA is about "
            f"{_format_minutes(route.eta_minutes)} minutes, with {risk} estimated flood exposure."
        )
        return f"{answer} {tradeoff}" if tradeoff else answer

    def _supplier_answer(self, context: CopilotContext, language: str) -> str:
        if not context.impacted_suppliers:
            if language == "id":
                return (
                    "Tidak ada pemasok yang tercatat terdampak dalam simulasi ini, sehingga bukti yang tersedia "
                    "tidak mendukung penentuan pemasok paling terdampak."
                )
            return (
                "No supplier is recorded as impacted in this simulation, so the available evidence does not support "
                "naming a most-affected supplier."
            )
        supplier = context.impacted_suppliers[0]
        if language == "id":
            return (
                f"{supplier} tercatat sebagai pemasok terdampak. Evidence saat ini tidak menyediakan skor yang "
                "cukup untuk memberi peringkat lebih lanjut antar pemasok."
            )
        return (
            f"{supplier} is recorded as an impacted supplier. The current evidence does not provide enough "
            "supplier-level scoring to rank it against other suppliers."
        )

    def _bottleneck_answer(self, context: CopilotContext, language: str) -> str:
        if not context.prioritized_issues:
            if language == "id":
                return "Tidak ada hambatan utama yang teridentifikasi dalam konteks simulasi saat ini."
            return "No primary bottleneck is identified in the current simulation context."
        issue = context.prioritized_issues[0]
        subject = _safe_issue_text(
            issue.subject,
            "kendala operasional utama" if language == "id" else "the primary operational constraint",
        )
        if language == "id":
            return (
                f"Hambatan paling penting adalah {subject} dengan tingkat keparahan "
                f"{_risk_label(issue.severity, language)}. Simulasi menempatkannya sebagai isu prioritas tertinggi."
            )
        return (
            f"The most important bottleneck is {subject}, with {_risk_label(issue.severity, language)} severity. "
            "The simulation ranks it as the highest-priority recorded issue."
        )

    def _orders_answer(self, context: CopilotContext, language: str) -> str:
        count = len(context.impacted_orders)
        if count == 0:
            return (
                "Tidak ada pesanan terdampak yang tercatat dalam simulasi ini."
                if language == "id"
                else "No impacted orders are recorded in this simulation."
            )
        if language == "id":
            return (
                f"Terdapat {count} pesanan terdampak. ID internal disembunyikan secara default; alasan prioritas "
                "hanya dapat dijelaskan jika tercatat dalam rencana pemulihan."
            )
        return (
            f"There are {count} impacted orders. Internal IDs are hidden by default; priority rationale is "
            "available only where the recovery plan records it."
        )

    def _tradeoff_answer(self, context: CopilotContext, language: str) -> str:
        route = _selected_recovery_route(context)
        if route is None:
            if language == "id":
                return "Trade-off pemulihan belum tersedia karena rute pemulihan belum tercatat."
            return "A recovery trade-off is unavailable because no recovery route is recorded."
        tradeoff = _route_tradeoff(context, route, language)
        if tradeoff:
            return tradeoff
        if language == "id":
            return "Simulasi saat ini tidak mencatat trade-off material untuk rute pemulihan terpilih."
        return "The current simulation does not record a material trade-off for the selected recovery route."

    def _recovery_answer(self, context: CopilotContext, language: str) -> str:
        if not context.recovery_actions:
            if language == "id":
                return "Rencana pemulihan belum tersedia dalam konteks simulasi saat ini."
            return "A recovery plan is not available in the current simulation context."
        categories = {item.category for item in context.recovery_actions}
        if language == "id":
            return (
                f"Rencana pemulihan memuat {len(context.recovery_actions)} tindakan pada "
                f"{len(categories)} area operasional. Rencana tersebut memprioritaskan kelayakan pengiriman dan "
                "pemenuhan pesanan dalam batas yang telah dihitung."
            )
        return (
            f"The recovery plan contains {len(context.recovery_actions)} actions across "
            f"{len(categories)} operational areas. It prioritizes feasible delivery and order fulfillment within "
            "the computed constraints."
        )

    def _dynamic_hazard_answer(self, context: CopilotContext, language: str) -> str:
        if context.hazard is None:
            if language == "id":
                return "Simulasi ini menggunakan historical replay; tidak ada skenario Dynamic Hazard yang aktif."
            return "This simulation uses historical replay; no Dynamic Hazard scenario is active."
        if language == "id":
            return (
                f"Skenario hujan {context.hazard.rainfall_scenario} adalah kondisi what-if berbasis pola historis "
                "untuk membandingkan risiko jalan relatif. Skenario ini bukan cuaca langsung atau probabilitas "
                "banjir terkalibrasi."
            )
        return (
            f"Rainfall scenario {context.hazard.rainfall_scenario} is a historical-derived what-if condition for "
            "comparing relative road risk. It is not live weather or a calibrated flood probability."
        )

    @staticmethod
    def _unavailable(language: str) -> str:
        if language == "id":
            return "Informasi tersebut tidak tersedia dalam konteks simulasi saat ini."
        return "That information is not available in the current simulation context."
