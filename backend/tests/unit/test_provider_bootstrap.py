import pytest

from app.bootstrap import build_container
from app.core.config import Settings
from app.llm.failover import FailoverProvider
from app.llm.mock import MockLLMProvider
from app.llm.openai_compatible import OpenAICompatibleProvider


def test_bootstrap_uses_mock_provider_by_default(tmp_path):
    container = build_container(
        Settings(
            app_env="test",
            session_secret="secret",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite'}",
            llm_provider="mock",
        )
    )
    assert isinstance(container.provider, MockLLMProvider)


def test_bootstrap_falls_back_to_mock_when_incomplete(tmp_path):
    """缺少 API Key 等配置时降级为 mock，保证服务可启动。"""
    container = build_container(
        Settings(
            app_env="test",
            session_secret="secret",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite'}",
            llm_provider="openai-compatible",
            llm_base_url="",
            llm_api_key="",
            llm_model="",
        )
    )
    assert isinstance(container.provider, MockLLMProvider)


def test_bootstrap_rejects_unknown_provider(tmp_path):
    with pytest.raises(ValueError, match="unsupported LLM_PROVIDER"):
        build_container(
            Settings(
                app_env="test",
                session_secret="secret",
                database_url=f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite'}",
                llm_provider="unknown-provider",
            )
        )


def test_bootstrap_builds_openai_provider(tmp_path):
    container = build_container(
        Settings(
            app_env="test",
            session_secret="secret",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite'}",
            llm_provider="openai-compatible",
            llm_base_url="https://example.test/v1",
            llm_api_key="secret-key",
            llm_model="model",
        )
    )
    assert isinstance(container.provider, FailoverProvider)
    assert isinstance(container.provider.primary, OpenAICompatibleProvider)


def test_bootstrap_builds_group_provider(tmp_path):
    container = build_container(
        Settings(
            app_env="test",
            session_secret="secret",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite'}",
            llm_provider="openai-compatible",
            llm_base_url="https://example.test/v1",
            llm_api_key="secret-key",
            llm_model="model",
            group_llm_base_url="https://group.test/v1",
            group_llm_api_key="group-key",
            group_llm_model="group-model",
        )
    )
    assert isinstance(container.runtime.group_provider, OpenAICompatibleProvider)
