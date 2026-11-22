import asyncio
import sqlite3
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.core.config import Settings
from app.infrastructure.db.models import Conversation, Memory, Message, Task
from app.infrastructure.db.session import create_engine, create_session_factory
from scripts.migrate_mvp_data import migrate


def test_migrate_legacy_database(tmp_path):
    source = tmp_path / "legacy.db"
    now = datetime.now(UTC).isoformat()
    connection = sqlite3.connect(source)
    try:
        connection.executescript(
            """
            CREATE TABLE users(id TEXT PRIMARY KEY, display_name TEXT, timezone TEXT, created_at TEXT);
            CREATE TABLE conversations(id TEXT PRIMARY KEY,user_id TEXT,title TEXT,next_message_seq INTEGER,created_at TEXT,updated_at TEXT);
            CREATE TABLE messages(id TEXT PRIMARY KEY,user_id TEXT,conversation_id TEXT,role TEXT,seq INTEGER,content TEXT,created_at TEXT);
            CREATE TABLE memories(id TEXT PRIMARY KEY,user_id TEXT,type TEXT,subject TEXT,content TEXT,normalized_key TEXT,status TEXT,created_at TEXT,updated_at TEXT);
            CREATE TABLE tasks(id TEXT PRIMARY KEY,user_id TEXT,title TEXT,status TEXT,due_at TEXT,remind_at TEXT,notified_at TEXT,created_at TEXT,updated_at TEXT);
            CREATE TABLE notifications(id INTEGER PRIMARY KEY,user_id TEXT,type TEXT,payload_json TEXT,created_at TEXT,read_at TEXT);
            """
        )
        connection.execute("INSERT INTO users VALUES(?,?,?,?)", ("u", "User", "Asia/Shanghai", now))
        connection.execute(
            "INSERT INTO conversations VALUES(?,?,?,?,?,?)", ("c", "u", "Title", 2, now, now)
        )
        connection.execute(
            "INSERT INTO messages VALUES(?,?,?,?,?,?,?)", ("m", "u", "c", "user", 1, "hello", now)
        )
        connection.execute(
            "INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?)",
            ("mem", "u", "fact", "我", "content", "key", "active", now, now),
        )
        connection.execute(
            "INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)",
            ("t", "u", "todo", "pending", None, None, None, now, now),
        )
        connection.commit()
    finally:
        connection.close()

    target = tmp_path / "target.db"
    target_url = f"sqlite+aiosqlite:///{target}"
    report = asyncio.run(migrate(source, target_url, dry_run=False))
    assert report.messages == 1

    async def counts():
        engine = create_engine(
            Settings(database_url=target_url, app_env="test", session_secret="test")
        )
        sessions = create_session_factory(engine)
        async with sessions() as session:
            values = [
                await session.scalar(select(func.count()).select_from(model))
                for model in (Conversation, Message, Memory, Task)
            ]
        await engine.dispose()
        return values

    assert asyncio.run(counts()) == [1, 1, 1, 1]
