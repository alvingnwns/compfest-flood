from __future__ import annotations

import logging

from app.core.config import Settings

from .context_builder import suggested_questions
from .providers.deterministic import DeterministicCopilotProvider
from .providers.gemini import GeminiCopilotProvider
from .providers.openrouter_qwen import OpenRouterQwenCopilotProvider
from .response_policy import ResponsePolicyViolation, classify_response_policy, finalize_provider_answer
from .schemas import CopilotContext, CopilotRequest, CopilotResponse

logger = logging.getLogger(__name__)


def _http_status(error: Exception) -> int | None:
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None) or getattr(error, "status_code", None)
    code = getattr(error, "code", None)
    if isinstance(status_code, int):
        return status_code
    return code if isinstance(code, int) else None


def _trace_attempt(provider: str, status: str, reason_code: str | None = None) -> None:
    logger.info(
        "copilot_provider_attempt provider=%s status=%s reason_code=%s",
        provider,
        status,
        reason_code or "none",
    )


def _fallback_reason(error: Exception) -> str:
    if isinstance(error, ResponsePolicyViolation):
        return f"gemini_guardrail_{error.reason_code}"
    status_code = _http_status(error)
    name = type(error).__name__.casefold()
    message = str(error).casefold()
    if "timeout" in name or "timeout" in message:
        return "gemini_timeout"
    if status_code == 429 or any(term in message for term in ("quota", "resource_exhausted", "429")):
        return "gemini_quota"
    if status_code in {401, 403}:
        return "gemini_auth_error"
    if status_code == 404 or any(term in message for term in ("model", "not found", "404")):
        return "gemini_model_unavailable"
    if status_code == 400:
        return "gemini_request_invalid"
    if isinstance(error, (ValueError, TypeError)):
        return "gemini_malformed_response"
    return "gemini_provider_error"


def _openrouter_fallback_reason(error: Exception) -> str:
    if isinstance(error, ResponsePolicyViolation):
        return f"openrouter_guardrail_{error.reason_code}"
    status_code = _http_status(error)
    name = type(error).__name__.casefold()
    message = str(error).casefold()
    if "timeout" in name or "timeout" in message:
        return "openrouter_timeout"
    if status_code == 429 or any(term in message for term in ("quota", "rate limit", "429")):
        return "openrouter_quota"
    if status_code in {401, 403}:
        return "openrouter_auth_error"
    if status_code == 404 or any(term in message for term in ("model", "not found", "404")):
        return "openrouter_model_unavailable"
    if status_code == 400:
        return "openrouter_request_invalid"
    if isinstance(error, (ValueError, TypeError)):
        return "openrouter_malformed_response"
    return "openrouter_provider_error"


def answer_copilot(request: CopilotRequest, context: CopilotContext, settings: Settings) -> CopilotResponse:
    fallback = DeterministicCopilotProvider()
    questions = suggested_questions(context)
    response_policy = classify_response_policy(request.message, request.recent_messages)
    if settings.explanation_mode == "deterministic":
        _trace_attempt("gemini", "skipped", "deterministic_mode")
        _trace_attempt("qwen", "skipped", "deterministic_mode")
        _trace_attempt("deterministic", "success")
        return CopilotResponse(
            answer=finalize_provider_answer(fallback.generate(request, context), response_policy, context),
            provider="deterministic",
            suggested_questions=questions,
            fallback_reason="deterministic_mode",
        )

    gemini_key = settings.gemini_api_key.get_secret_value().strip() if settings.gemini_api_key else ""
    gemini_reason = "gemini_key_missing"
    if not gemini_key:
        _trace_attempt("gemini", "skipped", gemini_reason)
    elif not settings.gemini_model.strip():
        gemini_reason = "gemini_model_missing"
        _trace_attempt("gemini", "skipped", gemini_reason)
    else:
        try:
            answer = GeminiCopilotProvider(
                api_key=gemini_key,
                model=settings.gemini_model,
                timeout_ms=settings.gemini_timeout_ms,
            ).generate(request, context)
            accepted = finalize_provider_answer(answer, response_policy, context)
            _trace_attempt("gemini", "success")
            return CopilotResponse(
                answer=accepted,
                provider="gemini",
                suggested_questions=questions,
            )
        except Exception as error:
            gemini_reason = _fallback_reason(error)
            _trace_attempt("gemini", "failed", gemini_reason)

    openrouter_key = settings.openrouter_api_key.get_secret_value().strip() if settings.openrouter_api_key else ""
    openrouter_reason = "openrouter_key_missing"
    if not openrouter_key:
        _trace_attempt("qwen", "skipped", openrouter_reason)
    elif not settings.openrouter_base_url.strip():
        openrouter_reason = "openrouter_base_url_missing"
        _trace_attempt("qwen", "skipped", openrouter_reason)
    elif not settings.openrouter_qwen_model.strip():
        openrouter_reason = "openrouter_model_missing"
        _trace_attempt("qwen", "skipped", openrouter_reason)
    else:
        try:
            answer = OpenRouterQwenCopilotProvider(
                api_key=openrouter_key,
                base_url=settings.openrouter_base_url,
                model=settings.openrouter_qwen_model,
            ).generate(request, context)
            accepted = finalize_provider_answer(answer, response_policy, context)
            _trace_attempt("qwen", "success")
            return CopilotResponse(
                answer=accepted,
                provider="qwen",
                suggested_questions=questions,
                fallback_reason=gemini_reason,
            )
        except Exception as error:
            openrouter_reason = _openrouter_fallback_reason(error)
            _trace_attempt("qwen", "failed", openrouter_reason)

    fallback_reason = openrouter_reason if openrouter_key else gemini_reason
    _trace_attempt("deterministic", "success", fallback_reason)

    return CopilotResponse(
        answer=finalize_provider_answer(fallback.generate(request, context), response_policy, context),
        provider="deterministic",
        suggested_questions=questions,
        fallback_reason=fallback_reason,
    )
