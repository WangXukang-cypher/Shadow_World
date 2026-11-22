import asyncio
from typing import Any

from .db import Database


class AsyncDatabase:
    """Moves the synchronous SQLite repository off the event-loop thread."""

    def __init__(self, database: Database):
        self.sync = database

    async def create_conversation(self, user_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self.sync.create_conversation, user_id)

    async def get_conversation(self, conversation_id: str, user_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self.sync.get_conversation, conversation_id, user_id)

    async def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.sync.list_conversations, user_id)

    async def add_message(
        self, conversation_id: str, user_id: str, role: str, content: str
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.sync.add_message, conversation_id, user_id, role, content
        )

    async def list_messages(self, conversation_id: str, user_id: str) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.sync.list_messages, conversation_id, user_id)

    async def create_memory(
        self, user_id: str, content: str, memory_type: str = "fact", subject: str = "我"
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.sync.create_memory, user_id, content, memory_type, subject
        )

    async def list_memories(self, user_id: str) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.sync.list_memories, user_id)

    async def create_task(
        self, user_id: str, title: str, remind_at: str | None = None
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self.sync.create_task, user_id, title, remind_at)

    async def list_tasks(self, user_id: str) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.sync.list_tasks, user_id)

    async def create_run(self, user_id: str, conversation_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self.sync.create_run, user_id, conversation_id)

    async def finish_run(
        self, run_id: str, status: str, route: str, error_code: str | None = None
    ) -> None:
        await asyncio.to_thread(self.sync.finish_run, run_id, status, route, error_code)

    async def due_tasks(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.sync.due_tasks)

    async def mark_task_notified(self, task_id: str) -> None:
        await asyncio.to_thread(self.sync.mark_task_notified, task_id)

    async def create_notification(
        self, user_id: str, notification_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.sync.create_notification, user_id, notification_type, payload
        )

    async def list_notifications(self, user_id: str, after_id: int = 0) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.sync.list_notifications, user_id, after_id)
