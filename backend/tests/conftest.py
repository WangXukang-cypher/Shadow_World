from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.application.services import DEFAULT_USER_ID
from app.core.config import Settings
from app.core.user_session import COOKIE_NAME, make_user_cookie
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        session_secret="test-secret-that-is-long-enough",
        reminder_poll_seconds=0.1,
        auto_create_schema=True,
        llm_provider="mock",
    )


@pytest.fixture
def app(settings: Settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        # 既有测试的数据都用默认用户 seed，这里预种指向该用户的签名 cookie
        test_client.cookies.set(
            COOKIE_NAME, make_user_cookie(DEFAULT_USER_ID, app.state.settings.session_secret)
        )
        yield test_client
