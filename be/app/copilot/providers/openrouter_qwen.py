from __future__ import annotations

import json

import httpx

from app.copilot.prompts import GROUNDING_PROMPT
from app.copilot.schemas import CopilotContext, CopilotRequest


class OpenRouterQwenCopilotProvider:
    name = "qwen"

    def __init__(self, *, api_key: str, base_url: str, model: str, timeout_ms: int = 30_000) -> None:
        self._api_key = api_key
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model
        self._timeout_seconds = timeout_ms / 1_000

    def generate(self, request: CopilotRequest, context: CopilotContext) -> str:
        qwen_system_prompt = GROUNDING_PROMPT.removesuffix("\n\nReturn JSON matching the requested schema.")
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
                        f"{qwen_system_prompt}\n\nFor this provider, return only the final answer as plain text."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False, separators=(",", ":")),
                },
            ],
            "max_tokens": 700,
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
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError("OpenRouter returned a malformed response envelope.") from error
        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenRouter returned an empty response.")
        answer = content.strip()
        if len(answer) > 4_000:
            raise ValueError("OpenRouter returned an oversized response.")
        return answer
