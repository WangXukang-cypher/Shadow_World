from pathlib import Path


def test_migrations_use_explicit_operations_not_create_all():
    versions = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    for migration in versions.glob("*.py"):
        assert "create_all" not in migration.read_text(encoding="utf-8")
