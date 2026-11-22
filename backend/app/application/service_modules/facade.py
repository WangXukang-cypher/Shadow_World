from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .base import DEFAULT_USER_ID
from .conversation_service import ConversationService
from .memory_service import MemoryService
from .notification_service import NotificationService
from .people_service import PeopleService
from .run_service import RunService
from .skill_service import SkillService
from .task_service import TaskService
from .tool_call_service import ToolCallService
from .user_llm_service import UserLLMService
from .user_service import UserService


class ApplicationService:
    """Compatibility facade while API/runtime migrate to domain services."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self.sessions = sessions
        self.users = UserService(sessions)
        self.conversations = ConversationService(sessions)
        self.runs = RunService(sessions)
        self.memories = MemoryService(sessions)
        self.tasks = TaskService(sessions)
        self.notifications = NotificationService(sessions)
        self.tool_calls = ToolCallService(sessions)
        self.skills = SkillService(sessions)
        self.people = PeopleService(sessions)
        self.user_llm = UserLLMService(sessions)

    async def get_user_llm_setting(self, user_id: str):
        return await self.user_llm.get(user_id)

    async def upsert_user_llm_setting(
        self, user_id: str, provider: str, base_url: str, api_key: str, model: str
    ):
        return await self.user_llm.upsert(user_id, provider, base_url, api_key, model)

    async def ensure_default_user(self, timezone: str):
        return await self.users.ensure_default_user(timezone)

    async def create_conversation(self, user_id: str, title: str = "", is_group: bool = False, persona_ids: list | None = None):
        return await self.conversations.create(user_id, title, is_group=is_group, persona_ids=persona_ids)

    async def list_conversations(self, user_id: str):
        return await self.conversations.list(user_id)

    async def get_conversation(self, user_id: str, conversation_id: str):
        return await self.conversations.get(user_id, conversation_id)

    async def get_conversation_with_messages(self, user_id: str, conversation_id: str):
        return await self.conversations.get_with_messages(user_id, conversation_id)

    async def patch_conversation(self, user_id: str, conversation_id: str, title: str | None = None, persona_ids: list | None = None):
        return await self.conversations.patch(user_id, conversation_id, title, persona_ids)

    async def add_message(self, user_id: str, conversation_id: str, role: str, content: str, persona_name: str | None = None, persona_avatar: str | None = None, reply_to_id: str | None = None):
        return await self.conversations.add_message(user_id, conversation_id, role, content, persona_name, persona_avatar, reply_to_id)

    async def delete_conversation(self, user_id: str, conversation_id: str):
        return await self.conversations.delete(user_id, conversation_id)

    async def create_run(self, user_id: str, conversation_id: str, input_message_id: str):
        return await self.runs.create(user_id, conversation_id, input_message_id)

    async def get_run(self, user_id: str, run_id: str):
        return await self.runs.get(user_id, run_id)

    async def set_run_status(
        self,
        run_id: str,
        status: str,
        route: str,
        output_message_id: str | None = None,
        error_code: str | None = None,
        **metrics,
    ):
        return await self.runs.set_status(
            run_id,
            status,
            route,
            output_message_id,
            error_code,
            **metrics,
        )

    async def request_run_cancel(self, user_id: str, run_id: str):
        return await self.runs.request_cancel(user_id, run_id)

    async def fail_stale_runs(self) -> int:
        return await self.runs.fail_stale_runs()

    async def is_run_cancel_requested(self, run_id: str):
        return await self.runs.is_cancel_requested(run_id)

    async def append_run_event(self, run_id: str, event_type: str, payload: dict[str, Any]):
        return await self.runs.append_event(run_id, event_type, payload)

    async def list_run_events(self, user_id: str, run_id: str, after_seq: int = 0):
        return await self.runs.list_events(user_id, run_id, after_seq)

    async def create_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str = "fact",
        subject: str = "我",
        source_message_id: str | None = None,
        tags: str | None = None,
    ):
        return await self.memories.create(
            user_id, content, memory_type, subject, source_message_id, tags=tags
        )

    async def list_memories(self, user_id: str):
        return await self.memories.list(user_id)

    async def create_task(
        self,
        user_id: str,
        title: str,
        remind_at: datetime | None = None,
        due_at: datetime | None = None,
        source_message_id: str | None = None,
    ):
        return await self.tasks.create(user_id, title, remind_at, due_at, source_message_id)

    async def list_tasks(self, user_id: str):
        return await self.tasks.list(user_id)

    async def claim_due_tasks(self, limit: int = 100):
        return await self.tasks.claim_due(limit)

    async def create_notification(
        self, user_id: str, notification_type: str, payload: dict[str, Any]
    ):
        return await self.notifications.create(user_id, notification_type, payload)

    async def list_notifications(self, user_id: str, after_id: int = 0, limit: int = 100):
        return await self.notifications.list(user_id, after_id, limit)

    async def delete_notification(self, user_id: str, notification_id: int) -> None:
        return await self.notifications.delete(user_id, notification_id)

    async def clear_notifications(self, user_id: str) -> None:
        return await self.notifications.delete_all(user_id)

    async def get_tool_call_by_idempotency_key(self, key: str):
        return await self.tool_calls.get_by_idempotency_key(key)

    async def create_tool_call(self, **kwargs):
        return await self.tool_calls.create(**kwargs)

    async def complete_tool_call(self, *args, **kwargs):
        return await self.tool_calls.complete(*args, **kwargs)

    async def fail_tool_call(self, *args, **kwargs):
        return await self.tool_calls.fail(*args, **kwargs)

    async def list_tool_calls(self, run_id: str):
        return await self.tool_calls.list_for_run(run_id)


__all__ = ["DEFAULT_USER_ID", "ApplicationService"]
