from fastapi import APIRouter, Request

from app.copilot.context_builder import build_copilot_context
from app.copilot.schemas import CopilotRequest, CopilotResponse
from app.copilot.service import answer_copilot
from app.core.config import Settings

router = APIRouter(prefix="/api/simulations", tags=["copilot"])


@router.post("/{simulation_id}/copilot", response_model=CopilotResponse, response_model_exclude_none=True)
def ask_copilot(simulation_id: str, request_body: CopilotRequest, request: Request) -> CopilotResponse:
    context = build_copilot_context(simulation_id)
    settings: Settings = request.app.state.settings
    return answer_copilot(request_body, context, settings)
