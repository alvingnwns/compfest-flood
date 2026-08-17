from __future__ import annotations

from app.core.config import Settings

from .context_builder import suggested_questions
from .providers.deterministic import DeterministicCopilotProvider
from .providers.gemini import GeminiCopilotProvider
from .providers.openrouter_qwen import OpenRouterQwenCopilotProvider
from .response_policy import classify_response_policy, finalize_provider_answer
from .schemas import CopilotContext, CopilotRequest, CopilotResponse


def _fallback_reason(error: Exception) -> str:
    name = type(error).__name__.casefold()
    message = str(error).casefold()
    if "timeout" in name or "timeout" in message:
        return "gemini_timeout"
    if any(term in message for term in ("quota", "resource_exhausted", "429")):
        return "gemini_quota"
    if any(term in message for term in ("model", "not found", "404")):
        return "gemini_model_unavailable"
    if isinstance(error, (ValueError, TypeError)):
        return "gemini_malformed_response"
    return "gemini_provider_error"


def _openrouter_fallback_reason(error: Exception) -> str:
    name = type(error).__name__.casefold()
    message = str(error).casefold()
    if "timeout" in name or "timeout" in message:
        return "openrouter_timeout"
    if any(term in message for term in ("quota", "rate limit", "429")):
        return "openrouter_quota"
    if any(term in message for term in ("model", "not found", "404")):
        return "openrouter_model_unavailable"
    if isinstance(error, (ValueError, TypeError)):
        return "openrouter_malformed_response"
    return "openrouter_provider_error"


def answer_copilot(request: CopilotRequest, context: CopilotContext, settings: Settings) -> CopilotResponse:
    fallback = DeterministicCopilotProvider()
    questions = suggested_questions(context)
    response_policy = classify_response_policy(request.message)
    if settings.explanation_mode == "deterministic":
        return CopilotResponse(
            answer=finalize_provider_answer(fallback.generate(request, context), response_policy, context),
            provider="deterministic",
            suggested_questions=questions,
            fallback_reason="deterministic_mode",
        )

    gemini_key = settings.gemini_api_key.get_secret_value().strip() if settings.gemini_api_key else ""
    gemini_reason = "gemini_key_missing"
    if gemini_key:
        try:
            answer = GeminiCopilotProvider(
                api_key=gemini_key,
                model=settings.gemini_model,
                timeout_ms=settings.gemini_timeout_ms,
            ).generate(request, context)
            return CopilotResponse(
                answer=finalize_provider_answer(answer, response_policy, context),
                provider="gemini",
                suggested_questions=questions,
            )
        except Exception as error:
            gemini_reason = _fallback_reason(error)

    openrouter_key = settings.openrouter_api_key.get_secret_value().strip() if settings.openrouter_api_key else ""
    if openrouter_key:
        try:
            answer = OpenRouterQwenCopilotProvider(
                api_key=openrouter_key,
                base_url=settings.openrouter_base_url,
                model=settings.openrouter_qwen_model,
            ).generate(request, context)
            return CopilotResponse(
                answer=finalize_provider_answer(answer, response_policy, context),
                provider="qwen",
                suggested_questions=questions,
                fallback_reason=gemini_reason,
            )
        except Exception as error:
            fallback_reason = _openrouter_fallback_reason(error)
    else:
        fallback_reason = gemini_reason

    return CopilotResponse(
        answer=finalize_provider_answer(fallback.generate(request, context), response_policy, context),
        provider="deterministic",
        suggested_questions=questions,
        fallback_reason=fallback_reason,
    )
