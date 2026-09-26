from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
REPOSITORY_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        repository_dotenv = DotEnvSettingsSource(
            settings_cls,
            env_file=REPOSITORY_ENV_FILE,
            env_file_encoding="utf-8",
        )
        return init_settings, env_settings, dotenv_settings, repository_dotenv, file_secret_settings

    app_env: Literal["development", "test", "production"] = "development"
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    frontend_origin: str = "http://localhost:3000"
    data_dir: Path = DEFAULT_DATA_DIR
    engine_mode: Literal["connected"] = "connected"
    explanation_mode: Literal["auto", "deterministic"] = "auto"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.5-flash"
    gemini_timeout_ms: int = Field(default=30_000, ge=10_000, le=30_000)
    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_qwen_model: str = "qwen/qwen3.5-flash-02-23"
    inventory_database_url: SecretStr | None = None
    inventory_model_dir: Path = Path(__file__).resolve().parents[2] / "artifacts" / "inventory"
    inventory_procurement_budget_idr: int = Field(default=1_000_000, ge=0)
    inventory_solver_timeout_seconds: float = Field(default=5.0, ge=0.1, le=30.0)
    risk_penalty_medium: int = Field(default=2, ge=0)
    risk_penalty_high: int = Field(default=5, ge=0)
    risk_penalty_critical: int = Field(default=15, ge=0)
    supplier_availability_medium: float = Field(default=0.85, ge=0, le=1)
    supplier_availability_high: float = Field(default=0.60, ge=0, le=1)
    supplier_availability_critical: float = Field(default=0.35, ge=0, le=1)
    objective_reward_normal: int = Field(default=100, ge=1)
    objective_reward_high: int = Field(default=1_000, ge=1)
    objective_reward_critical: int = Field(default=10_000, ge=1)
    objective_substitution_penalty: int = Field(default=20, ge=0)
    objective_delay_penalty: int = Field(default=5, ge=0)
    objective_risk_penalty: int = Field(default=50, ge=0)
    objective_transport_cost_scale: int = Field(default=10_000, ge=1)
    objective_production_penalty: int = Field(default=1, ge=0)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.frontend_origin.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
