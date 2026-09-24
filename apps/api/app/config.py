from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",extra="ignore")

    app_env: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False

    allow_dry_run_responses: bool = True
    autonomous_actions_enabled: bool = False
    response_dry_run: bool = True  # RESPONSE_DRY_RUN env var flips to live enforcement

    run_workers_inline: bool = False  # RUN_WORKERS_INLINE=true -> consumer+relay+batch run inside the API process
    batch_trigger_token: str = ""  # if set, POST /batch/run requires header X-Batch-Token

    api_url: str = "http://localhost:8000"
    frontend_origin: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://ps08:ps08_password@localhost:5432/ps08"
    redis_url: str = "redis://localhost:6379/0"

    websocket_ticket_ttl_seconds: int = Field(default=60, ge=10, le=300)
    event_retention_days: int = Field(default=30, ge=1)
    alert_stream_retention_days: int = Field(default=90, ge=1)

    jwt_issuer: str = ""
    jwt_audience: str = ""
    jwt_jwks_url: str = ""
    jwt_local_secret: str = ""  # HS256 fallback for local/test envs only

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env == "production":
            if self.debug:
                raise ValueError("debug cannot be enabled in production")
            if self.allow_dry_run_responses:
                raise ValueError("production response mode must be explicit")
            if not self.frontend_origin.startswith("https://"):
                raise ValueError("production frontend must use HTTPS")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
