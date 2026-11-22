from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
MISSION_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=MISSION_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    database_url: str = f"sqlite+aiosqlite:///{MISSION_DIR / 'data' / 'assistant-v1.db'}"
    session_secret: str = "generated-by-dev-script"
    timezone: str = "Asia/Shanghai"
    llm_provider: str = "mock"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = Field(default=60, ge=5, le=300)
    group_llm_base_url: str = ""
    group_llm_api_key: str = ""
    group_llm_model: str = ""
    auto_create_schema: bool = True
    max_active_runs_per_user: int = Field(default=2, ge=1, le=20)
    max_global_runs: int = Field(default=4, ge=1, le=100)
    message_rate_limit_per_minute: int = Field(default=20, ge=1, le=1000)
    reminder_poll_seconds: float = Field(default=5.0, ge=0.1, le=3600)
    run_event_retention_seconds: int = Field(default=3600, ge=60)

    @field_validator("session_secret")
    @classmethod
    def validate_secret(cls, value: str, info):
        insecure = {"", "replace-me", "development-only", "generated-by-dev-script"}
        app_env = str(info.data.get("app_env", "development")).lower()
        if value in insecure and app_env not in {"development", "dev", "test"}:
            raise ValueError("SESSION_SECRET must be configured outside development")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
