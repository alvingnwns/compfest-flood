from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel, ErrorResponse


class RunSimulationRequest(ApiModel):
    scenario_id: str = Field(min_length=1)


class Simulation(ApiModel):
    id: str
    scenario_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    created_at: datetime
    completed_at: datetime | None = None
    model_version: str | None = None
    optimizer_version: str | None = None
    data_mode: Literal["historical_snapshot", "live", "hybrid"]
    historical_data_status: Literal["available", "offline_snapshot", "unavailable"]
    error: ErrorResponse | None = None
