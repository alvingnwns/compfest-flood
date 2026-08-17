from __future__ import annotations

import json

from google import genai
from google.genai import types

from app.copilot.prompts import GROUNDING_PROMPT
from app.copilot.schemas import CopilotContext, CopilotProviderOutput, CopilotRequest


class GeminiCopilotProvider:
    name = "gemini"

    def __init__(self, *, api_key: str, model: str, timeout_ms: int) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_ms = timeout_ms

    def generate(self, request: CopilotRequest, context: CopilotContext) -> str:
        payload = {
            "currentSimulationEvidence": context.model_dump(mode="json", by_alias=True),
            "recentConversation": [item.model_dump(mode="json", by_alias=True) for item in request.recent_messages],
            "question": request.message,
        }
        client = genai.Client(
            api_key=self._api_key,
            http_options=types.HttpOptions(
                timeout=self._timeout_ms,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        try:
            response = client.models.generate_content(
                model=self._model,
                contents=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                config=types.GenerateContentConfig(
                    system_instruction=GROUNDING_PROMPT,
                    thinking_config=types.ThinkingConfig(thinking_level="minimal"),
                    max_output_tokens=700,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    response_mime_type="application/json",
                    response_json_schema=CopilotProviderOutput.model_json_schema(),
                ),
            )
        finally:
            client.close()

        if not response.text:
            raise ValueError("Gemini returned an empty response.")
        return CopilotProviderOutput.model_validate_json(response.text).answer
