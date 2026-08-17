from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.copilot.schemas import CopilotContext

ResponseLanguage = Literal["en", "id"]

_INDONESIAN_WORDS = {
    "apa",
    "apakah",
    "berapa",
    "besok",
    "dalam",
    "dan",
    "dengan",
    "dipilih",
    "jelaskan",
    "kenapa",
    "mana",
    "mengapa",
    "paling",
    "pemasok",
    "pengiriman",
    "penjualan",
    "risiko",
    "rute",
    "secara",
    "teknis",
    "terdampak",
    "tampilkan",
    "untuk",
    "yang",
}
_ENGLISH_WORDS = {
    "affected",
    "chosen",
    "details",
    "explain",
    "how",
    "is",
    "most",
    "route",
    "show",
    "supplier",
    "technical",
    "the",
    "this",
    "was",
    "what",
    "which",
    "why",
}
_TECHNICAL_TERMS = (
    "technical detail",
    "technical routing",
    "show technical",
    "jelaskan secara teknis",
    "jelasin secara teknis",
    "detail teknis",
    "osm segment",
    "osm id",
    "show the ids",
    "tampilkan id",
    "internal id",
    "networkx",
    "cp-sat",
    "constraint",
    "kendala solver",
    "exact risk score",
    "raw risk",
    "raw data",
    "data mentah",
    "model version",
)
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_INTERNAL_ID_RE = re.compile(
    r"\b(?:osm-\d[\w-]*|(?:route|ord|fac|sup|wh|sim)-[a-z0-9][\w-]*)\b",
    re.IGNORECASE,
)
_ENGINE_RE = re.compile(r"\b(?:NetworkX|CP-SAT|Random Forest)\b", re.IGNORECASE)
_RAW_SCORE_RE = re.compile(r"(?<![\d.])0\.\d{3,}(?!\d)")
_MONITORING_RECOMMENDATION_RE = re.compile(
    r"\b(?:requires? monitoring|should be monitored|keep an eye on|additional monitoring is recommended|"
    r"needs? monitoring|perlu dipantau|harus dipantau|memerlukan pemantauan|pemantauan tambahan)\b",
    re.IGNORECASE,
)
_MONITORING_EVIDENCE_RE = re.compile(r"\b(?:monitor(?:ing|ed)?|pantau|dipantau|pemantauan)\b", re.IGNORECASE)
_TRADEOFF_CLAIM_RE = re.compile(
    r"\b(?:trade-?off|tradeoff|kompromi|at the cost of|dengan konsekuensi)\b", re.IGNORECASE
)
_NO_TRADEOFF_RE = re.compile(
    r"\b(?:no material (?:computed )?trade-?off|does not record a material trade-?off|"
    r"tidak ada trade-?off material|tidak mencatat trade-?off material)\b",
    re.IGNORECASE,
)
_ACTION_TRADEOFF_RE = re.compile(
    r"\b(?:lower-priority (?:order )?(?:is )?delayed|delay(?:ed)? lower-priority|substitut(?:e|ion)|"
    r"additional transport cost|reduced production|reduced fulfillment|pesanan prioritas rendah ditunda|"
    r"menunda pesanan prioritas rendah|substitusi|biaya transportasi tambahan|pengurangan produksi|"
    r"pemenuhan berkurang)\b",
    re.IGNORECASE,
)
_RISK_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass(frozen=True)
class ResponsePolicy:
    question: str
    language: ResponseLanguage
    technical: bool

    @property
    def max_words(self) -> int:
        return 400 if self.technical else 120

    @property
    def max_output_tokens(self) -> int:
        return 700 if self.technical else 300


def _language_scores(text: str) -> tuple[int, int]:
    words = set(re.findall(r"[a-zA-Z]+", text.casefold()))
    return len(words & _ENGLISH_WORDS), len(words & _INDONESIAN_WORDS)


def detect_language(text: str) -> ResponseLanguage:
    english_score, indonesian_score = _language_scores(text)
    return "id" if indonesian_score > english_score else "en"


def requests_technical_detail(text: str) -> bool:
    question = text.casefold()
    return any(term in question for term in _TECHNICAL_TERMS)


def classify_response_policy(question: str) -> ResponsePolicy:
    return ResponsePolicy(
        question=question,
        language=detect_language(question),
        technical=requests_technical_detail(question),
    )


def build_response_instruction(question: str) -> str:
    policy = classify_response_policy(question)
    language = "Bahasa Indonesia" if policy.language == "id" else "English"
    if policy.technical:
        mode = (
            "The user explicitly requested technical detail. You may include relevant engine names, internal IDs, "
            "OSM segments, exact scores, or constraints only when they are present in the evidence and directly "
            "answer the question. Do not dump unrelated technical data."
        )
    else:
        mode = (
            "Use executive mode for an operations decision-maker. Answer directly in 20-120 words, normally in "
            "2-4 short sentences or paragraphs. Give at most three material reasons and the main trade-off when "
            "relevant. Never expose internal IDs, UUIDs, OSM segment IDs, engine names, exact raw risk scores, or "
            "implementation details. Use human-readable names and risk bands instead."
        )
    return (
        f"Required response language: {language}. Match the user's language exactly.\n"
        f"{mode}\n"
        "Answer only the question asked; do not summarize all context. Use only grounded evidence and meaningful "
        "computed numbers. Mention a trade-off only when the evidence shows a real computed downside such as a "
        "longer ETA, higher remaining risk, delayed lower-priority work, substitution, additional cost, reduced "
        "production, or reduced fulfillment elsewhere. Otherwise omit the trade-off. Never recommend monitoring, "
        "keeping an eye on something, or another operational action unless that action is explicitly present in "
        "the evidence. Return clean plain text with no Markdown syntax, headings, bullets, tables, or code."
    )


def _clean_plain_text(answer: str) -> str:
    cleaned = answer.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = cleaned.replace(chr(96), "").replace("**", "").replace("__", "")
    cleaned = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*[-*+]\s+", "", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _context_text(context: CopilotContext) -> str:
    action_text = " ".join(
        f"{action.what} {action.why} {action.expected_impact}" for action in context.recovery_actions
    )
    issue_text = " ".join(f"{issue.subject} {issue.description}" for issue in context.prioritized_issues)
    return f"{action_text} {issue_text}"


def _context_supports_monitoring(context: CopilotContext) -> bool:
    return _MONITORING_EVIDENCE_RE.search(_context_text(context)) is not None


def _context_has_material_tradeoff(context: CopilotContext, question: str) -> bool:
    baseline_by_destination = {}
    for route in context.routes:
        if route.route_type == "baseline":
            baseline_by_destination.setdefault(route.destination, route)
    selected_route_tradeoff = False
    route_tradeoff = False
    selected_recovery_seen = False
    for route in context.routes:
        if route.route_type != "recovery":
            continue
        is_selected_recovery = not selected_recovery_seen
        selected_recovery_seen = True
        baseline = baseline_by_destination.get(route.destination)
        if baseline is None:
            continue
        has_tradeoff = route.eta_minutes > baseline.eta_minutes or (
            _RISK_RANK[route.flood_exposure] > _RISK_RANK[baseline.flood_exposure]
        )
        route_tradeoff = route_tradeoff or has_tradeoff
        if is_selected_recovery:
            selected_route_tradeoff = has_tradeoff

    normalized_question = question.casefold()
    if any(term in normalized_question for term in ("route", "rute", "osm")):
        return selected_route_tradeoff
    if route_tradeoff:
        return True

    if _ACTION_TRADEOFF_RE.search(_context_text(context)):
        return True
    for metric in context.kpis:
        if metric.key == "orders-fulfilled" and metric.recovery < metric.baseline:
            return True
        if metric.key in {"failed-orders", "sales-exposure-risk"} and metric.recovery > metric.baseline:
            return True
    return False


def finalize_provider_answer(answer: str, policy: ResponsePolicy, context: CopilotContext) -> str:
    cleaned = _clean_plain_text(answer)
    if not cleaned:
        raise ValueError("Provider returned an empty response.")
    if len(cleaned.split()) > policy.max_words:
        raise ValueError("Provider response exceeded the response-policy word limit.")

    if not policy.technical:
        if _UUID_RE.search(cleaned) or _INTERNAL_ID_RE.search(cleaned):
            raise ValueError("Provider response exposed an internal identifier.")
        if _ENGINE_RE.search(cleaned):
            raise ValueError("Provider response exposed implementation details.")
        if _RAW_SCORE_RE.search(cleaned):
            raise ValueError("Provider response exposed an exact raw risk score.")

    if _MONITORING_RECOMMENDATION_RE.search(cleaned) and not _context_supports_monitoring(context):
        raise ValueError("Provider response invented an unsupported monitoring recommendation.")
    if (
        _TRADEOFF_CLAIM_RE.search(cleaned)
        and not _NO_TRADEOFF_RE.search(cleaned)
        and not _context_has_material_tradeoff(context, policy.question)
    ):
        raise ValueError("Provider response invented an unsupported trade-off.")

    english_score, indonesian_score = _language_scores(cleaned)
    if policy.language == "en" and indonesian_score >= 2 and indonesian_score > english_score:
        raise ValueError("Provider response language did not match the question.")
    if policy.language == "id" and english_score >= 2 and english_score > indonesian_score:
        raise ValueError("Provider response language did not match the question.")
    return cleaned
