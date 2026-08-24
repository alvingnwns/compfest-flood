from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import ApiModel, ErrorResponse


class VehicleOverride(ApiModel):
    """Per-vehicle operational-state override for a specific simulation run."""

    id: str
    available: bool | None = None
    capacity_units: int | None = Field(default=None, gt=0)


class CustomVehicle(ApiModel):
    """A vehicle created for one simulation run."""

    id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=120)
    capacity_units: int = Field(gt=0, le=1_000_000)
    available: bool = Field(default=True, strict=True)

    @field_validator("id", "label")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class InventoryOverride(ApiModel):
    """Per-warehouse/product inventory override for a specific simulation run."""

    facility_id: str
    product_id: str
    quantity: float = Field(ge=0)


class RunSimulationRequest(ApiModel):
    scenario_id: str = Field(min_length=1)
    analysis_mode: str = "historical-replay"
    region: str = "jakarta"
    rainfall_scenario: str | None = None
    business_snapshot_id: str | None = None
    vehicle_overrides: list[VehicleOverride] = Field(default_factory=list)
    custom_vehicles: list[CustomVehicle] = Field(default_factory=list)
    inventory_overrides: list[InventoryOverride] = Field(default_factory=list)


class ModelProvenance(ApiModel):
    training_data: str
    source: str
    target: str
    algorithm: str
    training_scope: str
    deployment_scope: str
    training_events: int = Field(gt=0)
    training_regions: int = Field(gt=0)
    jakarta_validation_status: Literal["not_validated", "validated"]
    probability_semantics: str


class DynamicHazardMetadata(ApiModel):
    rainfall_scenario: Literal["Q1", "Q2", "Q3", "Q4"]
    temporal_hazard_score: float = Field(ge=0, le=1)
    relative_hazard_index: float = Field(ge=0, le=1)
    probability_calibrated: Literal[False] = False
    model_version: str
    model_type: str
    fusion_method: Literal["logit_shift"] = "logit_shift"
    fusion_beta: float = 1.5
    risk_level_semantics: str


class Simulation(ApiModel):
    id: str
    scenario_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    created_at: datetime
    completed_at: datetime | None = None
    model_version: str | None = None
    model_provenance: ModelProvenance | None = None
    optimizer_version: str | None = None
    data_mode: Literal["historical_snapshot", "live", "hybrid"]
    historical_data_status: Literal["available", "offline_snapshot", "unavailable"]
    business_data_source: Literal["demo", "custom"] = "demo"
    business_snapshot_id: str | None = None
    analysis_mode: Literal["historical-replay", "scenario-simulation"] = "historical-replay"
    region: Literal["jakarta"] = "jakarta"
    hazard: DynamicHazardMetadata | None = None
    error: ErrorResponse | None = None
