from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError, ErrorCategory
from app.infrastructure.db.models import Conversation

DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


def utc_now() -> datetime:
    return datetime.now(UTC)


class ServiceBase:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self.sessions = sessions

    async def get_owned_conversation(
        self, session: AsyncSession, user_id: str, conversation_id: str
    ) -> Conversation:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise AppError(
                "CONVERSATION_NOT_FOUND",
                "会话不存在。",
                404,
                ErrorCategory.NOT_FOUND,
            )
        return conversation
