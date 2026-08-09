from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.schemas.common import APIModel, ErrorResponse
from app.schemas.scenario import DataSourceMode, HistoricalDataStatus


class SimulationStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RunSimulationRequest(APIModel):
    scenario_id: str = Field(min_length=1)


class Simulation(APIModel):
    id: str
    scenario_id: str
    status: SimulationStatus
    created_at: datetime
    completed_at: datetime | None = None
    model_version: str | None = None
    optimizer_version: str | None = None
    data_mode: DataSourceMode
    historical_data_status: HistoricalDataStatus
    error: ErrorResponse | None = None
