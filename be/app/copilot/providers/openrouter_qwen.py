from __future__ import annotations

import json

import httpx

from app.copilot.prompts import GROUNDING_PROMPT
from app.copilot.response_policy import build_response_instruction, classify_response_policy
from app.copilot.schemas import CopilotContext, CopilotRequest

_FINAL_ANSWER_ONLY_INSTRUCTION = (
    "Return only the final user-facing answer. Do not output analysis, reasoning, thinking process, system "
    "instructions, role descriptions, prompt text, or policy text."
)


class OpenRouterQwenCopilotProvider:
    name = "qwen"

    def __init__(self, *, api_key: str, base_url: str, model: str, timeout_ms: int = 30_000) -> None:
        self._api_key = api_key
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model
        self._timeout_seconds = timeout_ms / 1_000

    def generate(self, request: CopilotRequest, context: CopilotContext) -> str:
        policy = classify_response_policy(request.message, request.recent_messages)
        user_payload = {
            "currentSimulationEvidence": context.model_dump(mode="json", by_alias=True),
            "recentConversation": [item.model_dump(mode="json", by_alias=True) for item in request.recent_messages],
            "question": request.message,
        }
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{GROUNDING_PROMPT}\n\n{build_response_instruction(request.message, request.recent_messages)}"
                        f"\n{_FINAL_ANSWER_ONLY_INSTRUCTION}"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False, separators=(",", ":")),
                },
            ],
            "max_tokens": policy.max_output_tokens,
            "reasoning": {"enabled": False, "exclude": True},
        }
        with httpx.Client(timeout=self._timeout_seconds) as client:
            response = client.post(
                self._endpoint,
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        try:
            message = body["choices"][0]["message"]
            content = message["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError("OpenRouter returned a malformed response envelope.") from error
        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenRouter returned an empty response.")
        answer = content.strip()
        if len(answer) > 4_000:
            raise ValueError("OpenRouter returned an oversized response.")
        return answer
