import logging
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_INSECURE_SESSION_SECRETS = {
    "",
    "development-only",
    "generated-by-dev-script",
    "replace-me",
}


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    database_path: str = "./data/assistant.db"
    session_secret: str = "development-only"
    timezone: str = "Asia/Shanghai"
    llm_provider: str = "mock"
    max_active_runs_per_user: int = 2
    max_global_runs: int = 4
    message_rate_limit_per_minute: int = 20
    reminder_poll_seconds: float = 5.0


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _resolve_session_secret(app_env: str, configured: str) -> str:
    if configured not in _INSECURE_SESSION_SECRETS:
        return configured
    if app_env.lower() not in {"development", "dev", "test"}:
        raise ValueError("SESSION_SECRET must be configured outside development")
    generated = secrets.token_urlsafe(48)
    logger.warning(
        "SESSION_SECRET is unset or uses a placeholder; generated an ephemeral development secret"
    )
    return generated


def validate_settings(settings: Settings) -> None:
    if (
        settings.app_env.lower() not in {"development", "dev", "test"}
        and settings.session_secret in _INSECURE_SESSION_SECRETS
    ):
        raise ValueError("SESSION_SECRET must be configured outside development")


def load_settings() -> Settings:
    _load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    app_env = os.getenv("APP_ENV", "development")
    session_secret = _resolve_session_secret(
        app_env, os.getenv("SESSION_SECRET", "development-only")
    )
    return Settings(
        app_env=app_env,
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8000")),
        database_path=os.getenv("DATABASE_PATH", "./data/assistant.db"),
        session_secret=session_secret,
        timezone=os.getenv("TIMEZONE", "Asia/Shanghai"),
        llm_provider=os.getenv("LLM_PROVIDER", "mock"),
        max_active_runs_per_user=int(os.getenv("MAX_ACTIVE_RUNS_PER_USER", "2")),
        max_global_runs=int(os.getenv("MAX_GLOBAL_RUNS", "4")),
        message_rate_limit_per_minute=int(os.getenv("MESSAGE_RATE_LIMIT_PER_MINUTE", "20")),
        reminder_poll_seconds=float(os.getenv("REMINDER_POLL_SECONDS", "5")),
    )
