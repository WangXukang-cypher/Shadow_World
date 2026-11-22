#!/usr/bin/env python3
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings
from app.main import create_app


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else BACKEND_DIR / "openapi.json"
    app = create_app(
        Settings(
            app_env="test",
            session_secret="openapi-export-secret",
            database_url="sqlite+aiosqlite:///:memory:",
            auto_create_schema=False,
        )
    )
    output.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
