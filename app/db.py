from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .normalization import memory_normalized_key

DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: str):
        self.path = str(Path(path).expanduser().resolve())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.RLock()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    @contextmanager
    def readonly(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._write_lock:
            conn = self.connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def initialize(self) -> None:
        conn = self.connect()
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.commit()
        finally:
            conn.close()
        with self.transaction() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id),
                    title TEXT NOT NULL DEFAULT '',
                    next_message_seq INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id),
                    conversation_id TEXT NOT NULL REFERENCES conversations(id),
                    role TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(conversation_id, seq)
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id),
                    type TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    normalized_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, type, subject, normalized_key)
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id),
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    due_at TEXT,
                    remind_at TEXT,
                    notified_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id),
                    conversation_id TEXT NOT NULL REFERENCES conversations(id),
                    status TEXT NOT NULL,
                    route TEXT NOT NULL DEFAULT '',
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL REFERENCES users(id),
                    type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    read_at TEXT
                );
                """
            )
            conn.execute(
                "INSERT OR IGNORE INTO users(id, display_name, timezone, created_at) VALUES(?,?,?,?)",
                (DEFAULT_USER_ID, "本地用户", "Asia/Shanghai", utc_now()),
            )

    def create_conversation(self, user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
        item_id, now = str(uuid.uuid4()), utc_now()
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO conversations(id,user_id,title,created_at,updated_at) VALUES(?,?,?,?,?)",
                (item_id, user_id, "", now, now),
            )
        return self.get_conversation(item_id, user_id)

    def get_conversation(self, conversation_id: str, user_id: str) -> dict[str, Any]:
        with self.readonly() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id=? AND user_id=?",
                (conversation_id, user_id),
            ).fetchone()
        if row is None:
            raise KeyError("conversation not found")
        return dict(row)

    def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        with self.readonly() as conn:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE user_id=? ORDER BY updated_at DESC", (user_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def add_message(
        self, conversation_id: str, user_id: str, role: str, content: str
    ) -> dict[str, Any]:
        message_id, now = str(uuid.uuid4()), utc_now()
        with self.transaction() as conn:
            conversation = conn.execute(
                "SELECT next_message_seq,title FROM conversations WHERE id=? AND user_id=?",
                (conversation_id, user_id),
            ).fetchone()
            if conversation is None:
                raise KeyError("conversation not found")
            seq = int(conversation["next_message_seq"])
            conn.execute(
                "INSERT INTO messages(id,user_id,conversation_id,role,seq,content,created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (message_id, user_id, conversation_id, role, seq, content, now),
            )
            title = conversation["title"]
            if role == "user" and not title:
                title = " ".join(content.split())[:20] or "新会话"
            conn.execute(
                "UPDATE conversations SET next_message_seq=?, title=?, updated_at=? WHERE id=?",
                (seq + 1, title, now, conversation_id),
            )
        return {"id": message_id, "role": role, "seq": seq, "content": content, "created_at": now}

    def list_messages(self, conversation_id: str, user_id: str) -> list[dict[str, Any]]:
        self.get_conversation(conversation_id, user_id)
        with self.readonly() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id=? AND user_id=? ORDER BY seq ASC",
                (conversation_id, user_id),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_memory(
        self, user_id: str, content: str, memory_type: str = "fact", subject: str = "我"
    ) -> dict[str, Any]:
        key, now = memory_normalized_key(memory_type, subject, content), utc_now()
        with self.transaction() as conn:
            existing = conn.execute(
                "SELECT * FROM memories WHERE user_id=? AND type=? AND subject=? AND normalized_key=?",
                (user_id, memory_type, subject, key),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE memories SET updated_at=?, status='active' WHERE id=?",
                    (now, existing["id"]),
                )
                memory_id = existing["id"]
            else:
                memory_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO memories(id,user_id,type,subject,content,normalized_key,status,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (memory_id, user_id, memory_type, subject, content, key, "active", now, now),
                )
        return self.get_memory(memory_id, user_id)

    def get_memory(self, memory_id: str, user_id: str) -> dict[str, Any]:
        with self.readonly() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id=? AND user_id=?", (memory_id, user_id)
            ).fetchone()
        if row is None:
            raise KeyError("memory not found")
        return dict(row)

    def list_memories(self, user_id: str) -> list[dict[str, Any]]:
        with self.readonly() as conn:
            rows = conn.execute(
                "SELECT * FROM memories WHERE user_id=? AND status='active' ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_task(self, user_id: str, title: str, remind_at: str | None = None) -> dict[str, Any]:
        task_id, now = str(uuid.uuid4()), utc_now()
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO tasks(id,user_id,title,remind_at,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (task_id, user_id, title, remind_at, now, now),
            )
        return self.get_task(task_id, user_id)

    def get_task(self, task_id: str, user_id: str) -> dict[str, Any]:
        with self.readonly() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)
            ).fetchone()
        if row is None:
            raise KeyError("task not found")
        return dict(row)

    def list_tasks(self, user_id: str) -> list[dict[str, Any]]:
        with self.readonly() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE user_id=? AND status='pending' ORDER BY COALESCE(remind_at,'9999') ASC",
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_run(self, user_id: str, conversation_id: str) -> dict[str, Any]:
        self.get_conversation(conversation_id, user_id)
        run_id, now = str(uuid.uuid4()), utc_now()
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO runs(id,user_id,conversation_id,status,created_at) VALUES(?,?,?,?,?)",
                (run_id, user_id, conversation_id, "queued", now),
            )
        return {"id": run_id, "status": "queued", "conversation_id": conversation_id}

    def finish_run(
        self, run_id: str, status: str, route: str, error_code: str | None = None
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE runs SET status=?,route=?,error_code=?,completed_at=? WHERE id=?",
                (status, route, error_code, utc_now(), run_id),
            )

    def due_tasks(self) -> list[dict[str, Any]]:
        with self.readonly() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status='pending' AND remind_at IS NOT NULL "
                "AND notified_at IS NULL AND remind_at<=? ORDER BY remind_at ASC",
                (utc_now(),),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_task_notified(self, task_id: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE tasks SET notified_at=?,updated_at=? WHERE id=?",
                (utc_now(), utc_now(), task_id),
            )

    def create_notification(
        self, user_id: str, notification_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        now = utc_now()
        with self.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO notifications(user_id,type,payload_json,created_at) VALUES(?,?,?,?)",
                (user_id, notification_type, json.dumps(payload, ensure_ascii=False), now),
            )
            notification_id = cursor.lastrowid
        return {
            "id": notification_id,
            "type": notification_type,
            "payload": payload,
            "created_at": now,
        }

    def list_notifications(self, user_id: str, after_id: int = 0) -> list[dict[str, Any]]:
        with self.readonly() as conn:
            rows = conn.execute(
                "SELECT * FROM notifications WHERE user_id=? AND id>? ORDER BY id ASC LIMIT 100",
                (user_id, after_id),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "type": row["type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
