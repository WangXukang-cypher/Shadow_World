import pytest

from app.config import Settings, _resolve_session_secret, validate_settings


def test_placeholder_secret_is_replaced_in_development():
    secret = _resolve_session_secret("development", "generated-by-dev-script")
    assert secret != "generated-by-dev-script"
    assert len(secret) >= 48


def test_placeholder_secret_is_rejected_outside_development():
    with pytest.raises(ValueError, match="SESSION_SECRET"):
        _resolve_session_secret("production", "generated-by-dev-script")


def test_explicit_production_settings_reject_placeholder_secret():
    with pytest.raises(ValueError, match="SESSION_SECRET"):
        validate_settings(Settings(app_env="production", session_secret="development-only"))
