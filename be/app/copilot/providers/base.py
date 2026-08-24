from typing import Protocol

from app.copilot.schemas import CopilotContext, CopilotRequest


class CopilotProvider(Protocol):
    name: str

    def generate(self, request: CopilotRequest, context: CopilotContext) -> str: ...
