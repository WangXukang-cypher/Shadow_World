#!/usr/bin/env python3
import argparse
import asyncio
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.dialects.sqlite import insert

from app.core.config import Settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import Conversation, Memory, Message, Notification, Task, User
from app.infrastructure.db.session import create_engine, create_session_factory


@dataclass
class MigrationReport:
    users: int = 0
    conversations: int = 0
    messages: int = 0
    memories: int = 0
    tasks: int = 0
    notifications: int = 0


def read_rows(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not exists:
        return []
    return [dict(row) for row in connection.execute(f"SELECT * FROM {table}").fetchall()]


def parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


async def migrate(source: Path, target_url: str, dry_run: bool) -> MigrationReport:
    if not source.exists():
        raise FileNotFoundError(source)
    source_connection = sqlite3.connect(source)
    source_connection.row_factory = sqlite3.Row
    try:
        source_data = {
            table: read_rows(source_connection, table)
            for table in [
                "users",
                "conversations",
                "messages",
                "memories",
                "tasks",
                "notifications",
            ]
        }
    finally:
        source_connection.close()

    report = MigrationReport(**{name: len(rows) for name, rows in source_data.items()})
    if dry_run:
        return report

    settings = Settings(database_url=target_url, app_env="development")
    engine = create_engine(settings)
    sessions = create_session_factory(engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    converters = {
        "users": lambda row: {
            "id": row["id"],
            "display_name": row["display_name"],
            "timezone": row["timezone"],
            "created_at": parse_datetime(row["created_at"]),
        },
        "conversations": lambda row: {
            "id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "next_message_seq": row["next_message_seq"],
            "created_at": parse_datetime(row["created_at"]),
            "updated_at": parse_datetime(row["updated_at"]),
        },
        "messages": lambda row: {
            "id": row["id"],
            "user_id": row["user_id"],
            "conversation_id": row["conversation_id"],
            "role": row["role"],
            "seq": row["seq"],
            "content": row["content"],
            "status": "complete",
            "created_at": parse_datetime(row["created_at"]),
        },
        "memories": lambda row: {
            "id": row["id"],
            "user_id": row["user_id"],
            "type": row["type"],
            "subject": row["subject"],
            "content": row["content"],
            "normalized_key": row["normalized_key"],
            "status": row["status"],
            "created_at": parse_datetime(row["created_at"]),
            "updated_at": parse_datetime(row["updated_at"]),
        },
        "tasks": lambda row: {
            "id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "status": row["status"],
            "due_at": parse_datetime(row.get("due_at")),
            "remind_at": parse_datetime(row.get("remind_at")),
            "notified_at": parse_datetime(row.get("notified_at")),
            "created_at": parse_datetime(row["created_at"]),
            "updated_at": parse_datetime(row["updated_at"]),
        },
        "notifications": lambda row: {
            "id": row["id"],
            "user_id": row["user_id"],
            "type": row["type"],
            "payload": __import__("json").loads(row["payload_json"]),
            "created_at": parse_datetime(row["created_at"]),
            "read_at": parse_datetime(row.get("read_at")),
        },
    }
    model_map = {
        "users": User,
        "conversations": Conversation,
        "messages": Message,
        "memories": Memory,
        "tasks": Task,
        "notifications": Notification,
    }
    async with sessions.begin() as session:
        for table, rows in source_data.items():
            values = [converters[table](row) for row in rows]
            if values:
                await session.execute(
                    insert(model_map[table]).values(values).prefix_with("OR IGNORE")
                )
    await engine.dispose()
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", required=True, help="SQLAlchemy async database URL")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backup", action="store_true")
    args = parser.parse_args()
    if args.backup and not args.dry_run:
        backup = args.source.with_suffix(args.source.suffix + ".bak")
        shutil.copy2(args.source, backup)
        print(f"backup={backup}")
    report = asyncio.run(migrate(args.source, args.target, args.dry_run))
    print(report)


if __name__ == "__main__":
    main()
