from __future__ import annotations

import uuid

from sqlalchemy import select

from app.application.keyed_lock import KeyedLockPool
from app.infrastructure.db.models import (
    AgentRun,
    Conversation,
    Memory,
    Message,
    RunEvent,
    Task,
    ToolCallRecord,
)

from .base import ServiceBase, utc_now


class ConversationService(ServiceBase):
    def __init__(self, sessions):
        super().__init__(sessions)
        self.message_locks = KeyedLockPool()

    async def create(self, user_id: str, title: str = "", is_group: bool = False, persona_ids: list | None = None) -> Conversation:
        now = utc_now()
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            next_message_seq=1,
            is_group=is_group,
            persona_ids=persona_ids,
            created_at=now,
            updated_at=now,
        )
        async with self.sessions.begin() as session:
            session.add(conversation)
        return conversation

    async def list(self, user_id: str) -> list[Conversation]:
        async with self.sessions() as session:
            return list(
                await session.scalars(
                    select(Conversation)
                    .where(Conversation.user_id == user_id, Conversation.archived_at.is_(None))
                    .order_by(Conversation.updated_at.desc())
                )
            )

    async def get(self, user_id: str, conversation_id: str) -> Conversation:
        async with self.sessions() as session:
            return await self.get_owned_conversation(session, user_id, conversation_id)

    async def get_with_messages(
        self, user_id: str, conversation_id: str
    ) -> tuple[Conversation, list[Message]]:
        async with self.sessions() as session:
            conversation = await self.get_owned_conversation(session, user_id, conversation_id)
            messages = list(
                await session.scalars(
                    select(Message)
                    .where(
                        Message.user_id == user_id,
                        Message.conversation_id == conversation_id,
                    )
                    .order_by(Message.seq.asc())
                )
            )
            return conversation, messages

    async def patch(self, user_id: str, conversation_id: str, title: str | None = None, persona_ids: list | None = None) -> Conversation:
        async with self.sessions.begin() as session:
            conversation = await self.get_owned_conversation(session, user_id, conversation_id)
            if title is not None:
                conversation.title = title
            if persona_ids is not None:
                conversation.persona_ids = persona_ids
            conversation.updated_at = utc_now()
        return conversation

    async def add_message(
        self, user_id: str, conversation_id: str, role: str, content: str,
        persona_name: str | None = None, persona_avatar: str | None = None,
        reply_to_id: str | None = None,
    ) -> Message:
        async with self.message_locks.hold(conversation_id):
            async with self.sessions.begin() as session:
                conversation = await self.get_owned_conversation(session, user_id, conversation_id)
                seq = conversation.next_message_seq
                message = Message(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    conversation_id=conversation_id,
                    role=role,
                    seq=seq,
                    content=content,
                    status="complete",
                    persona_name=persona_name,
                    persona_avatar=persona_avatar,
                    reply_to_id=reply_to_id,
                    created_at=utc_now(),
                )
                conversation.next_message_seq = seq + 1
                if role == "user" and not conversation.title:
                    conversation.title = " ".join(content.split())[:20] or "新会话"
                conversation.updated_at = utc_now()
                session.add(message)
            return message

    async def delete(self, user_id: str, conversation_id: str) -> None:
        async with self.sessions.begin() as session:
            conversation = await self.get_owned_conversation(session, user_id, conversation_id)
            from sqlalchemy import delete as sql_delete
            from sqlalchemy import update as sql_update

            msg_ids = select(Message.id).where(Message.conversation_id == conversation_id)
            # 记忆/待办保留，仅断开对会话消息的来源引用，否则外键约束导致删除失败
            await session.execute(
                sql_update(Memory)
                .where(Memory.source_message_id.in_(msg_ids))
                .values(source_message_id=None)
            )
            await session.execute(
                sql_update(Task)
                .where(Task.source_message_id.in_(msg_ids))
                .values(source_message_id=None)
            )
            run_ids = select(AgentRun.id).where(AgentRun.conversation_id == conversation_id)
            await session.execute(sql_delete(ToolCallRecord).where(ToolCallRecord.run_id.in_(run_ids)))
            await session.execute(sql_delete(RunEvent).where(RunEvent.run_id.in_(run_ids)))
            await session.execute(sql_delete(AgentRun).where(AgentRun.conversation_id == conversation_id))
            await session.execute(sql_delete(Message).where(Message.conversation_id == conversation_id))
            await session.delete(conversation)
