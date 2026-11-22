import os
import sqlite3
import subprocess
from pathlib import Path


def alembic_env(database: Path) -> dict[str, str]:
    return {
        **os.environ,
        "APP_ENV": "test",
        "SESSION_SECRET": "test-secret",
        "DATABASE_URL": f"sqlite+aiosqlite:///{database}",
    }


def test_alembic_upgrades_existing_baseline_to_observability_schema(tmp_path):
    backend = Path(__file__).resolve().parents[2]
    database = tmp_path / "upgrade.db"
    subprocess.run(
        ["alembic", "upgrade", "20260817_0001"],
        cwd=backend,
        env=alembic_env(database),
        check=True,
        capture_output=True,
        text=True,
    )
    with sqlite3.connect(database) as connection:
        before = {row[1] for row in connection.execute("PRAGMA table_info(agent_runs)").fetchall()}
        assert "model_name" not in before
        assert not connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tool_calls'"
        ).fetchone()

    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=backend,
        env=alembic_env(database),
        check=True,
        capture_output=True,
        text=True,
    )
    with sqlite3.connect(database) as connection:
        after = {row[1] for row in connection.execute("PRAGMA table_info(agent_runs)").fetchall()}
        assert {"model_name", "iteration_count", "prompt_tokens", "completion_tokens"} <= after
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tool_calls'"
        ).fetchone()
