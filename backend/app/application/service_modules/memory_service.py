from __future__ import annotations

import uuid

from sqlalchemy import select

from app.agent.normalization import memory_normalized_key
from app.core.errors import AppError, ErrorCategory
from app.infrastructure.db.models import Memory, MemoryRelation

from .base import ServiceBase, utc_now


class MemoryService(ServiceBase):
    async def create(
        self,
        user_id: str,
        content: str,
        memory_type: str = "fact",
        subject: str = "我",
        source_message_id: str | None = None,
        image_path: str | None = None,
        image_description: str | None = None,
        tags: str | None = None,
        entity_type: str | None = None,
    ) -> Memory:
        key = memory_normalized_key(memory_type, subject, content)
        async with self.sessions.begin() as session:
            existing = await session.scalar(
                select(Memory).where(
                    Memory.user_id == user_id,
                    Memory.type == memory_type,
                    Memory.subject == subject,
                    Memory.normalized_key == key,
                )
            )
            if existing is not None:
                existing.status = "active"
                existing.updated_at = utc_now()
                if image_path:
                    existing.image_path = image_path
                if image_description:
                    existing.image_description = image_description
                return existing
            now = utc_now()
            memory = Memory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                type=memory_type,
                subject=subject,
                content=content,
                normalized_key=key,
                status="active",
                source_message_id=source_message_id,
                image_path=image_path,
                image_description=image_description,
                tags=tags,
                entity_type=entity_type,
                created_at=now,
                updated_at=now,
            )
            session.add(memory)
            return memory

    async def list(self, user_id: str) -> list[Memory]:
        async with self.sessions() as session:
            return list(
                await session.scalars(
                    select(Memory)
                    .where(Memory.user_id == user_id, Memory.status == "active")
                    .order_by(Memory.updated_at.desc())
                )
            )

    async def update(self, user_id: str, memory_id: str, content: str) -> Memory:
        async with self.sessions.begin() as session:
            memory = await session.get(Memory, memory_id)
            if memory is None or memory.user_id != user_id or memory.status != "active":
                raise AppError("MEMORY_NOT_FOUND", "记忆不存在。", 404, ErrorCategory.NOT_FOUND)
            memory.content = content
            memory.normalized_key = memory_normalized_key(
                memory.type, memory.subject, content
            )
            memory.updated_at = utc_now()
        return memory

    async def delete(self, user_id: str, memory_id: str) -> None:
        async with self.sessions.begin() as session:
            memory = await session.get(Memory, memory_id)
            if memory is None or memory.user_id != user_id:
                raise AppError("MEMORY_NOT_FOUND", "记忆不存在。", 404, ErrorCategory.NOT_FOUND)
            memory.status = "deleted"
            memory.updated_at = utc_now()

    async def add_relation(
        self, user_id: str, source_id: str, target_id: str, relation_type: str
    ) -> MemoryRelation:
        async with self.sessions.begin() as session:
            relation = MemoryRelation(
                id=str(uuid.uuid4()),
                user_id=user_id,
                source_memory_id=source_id,
                target_memory_id=target_id,
                relation_type=relation_type,
                created_at=utc_now(),
            )
            session.add(relation)
        return relation

    async def get_graph(self, user_id: str) -> dict:
        async with self.sessions() as session:
            memories = list(
                await session.scalars(
                    select(Memory)
                    .where(Memory.user_id == user_id, Memory.status == "active")
                    .order_by(Memory.updated_at.desc())
                )
            )
            relations = list(
                await session.scalars(
                    select(MemoryRelation).where(MemoryRelation.user_id == user_id)
                )
            )
        active_ids = {m.id for m in memories}
        nodes = [
            {
                "id": m.id,
                "content": m.content,
                "type": m.type,
                "subject": m.subject,
                "entity_type": m.entity_type,
                "tags": m.tags.split(",") if m.tags else [],
                "has_image": bool(m.image_path),
            }
            for m in memories
        ]
        edges = [
            {
                "id": r.id,
                "source": r.source_memory_id,
                "target": r.target_memory_id,
                "relation_type": r.relation_type,
            }
            for r in relations
            if r.source_memory_id in active_ids and r.target_memory_id in active_ids
        ]
        return {"nodes": nodes, "edges": edges}
