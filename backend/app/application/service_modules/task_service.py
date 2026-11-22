from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update

from app.core.errors import AppError, ErrorCategory
from app.infrastructure.db.models import Task

from .base import ServiceBase, utc_now


class TaskService(ServiceBase):
    async def create(
        self,
        user_id: str,
        title: str,
        remind_at: datetime | None = None,
        due_at: datetime | None = None,
        source_message_id: str | None = None,
    ) -> Task:
        now = utc_now()
        task = Task(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            status="pending",
            remind_at=remind_at,
            due_at=due_at,
            source_message_id=source_message_id,
            created_at=now,
            updated_at=now,
        )
        async with self.sessions.begin() as session:
            session.add(task)
        return task

    async def list(self, user_id: str, include_completed: bool = False) -> list[Task]:
        async with self.sessions() as session:
            conditions = [Task.user_id == user_id]
            if not include_completed:
                conditions.append(Task.status == "pending")
            return list(
                await session.scalars(
                    select(Task)
                    .where(*conditions)
                    .order_by(Task.remind_at.asc().nulls_last(), Task.created_at.desc())
                )
            )

    async def get(self, user_id: str, task_id: str) -> Task:
        async with self.sessions() as session:
            task = await session.get(Task, task_id)
            if task is None or task.user_id != user_id:
                raise AppError("TASK_NOT_FOUND", "待办不存在。", 404, ErrorCategory.NOT_FOUND)
            return task

    async def complete(self, user_id: str, task_id: str) -> Task:
        async with self.sessions.begin() as session:
            task = await session.get(Task, task_id)
            if task is None or task.user_id != user_id:
                raise AppError("TASK_NOT_FOUND", "待办不存在。", 404, ErrorCategory.NOT_FOUND)
            task.status = "completed"
            task.updated_at = utc_now()
        return task

    async def update(
        self,
        user_id: str,
        task_id: str,
        title: str | None = None,
        remind_at: datetime | None = None,
    ) -> Task:
        async with self.sessions.begin() as session:
            task = await session.get(Task, task_id)
            if task is None or task.user_id != user_id:
                raise AppError("TASK_NOT_FOUND", "待办不存在。", 404, ErrorCategory.NOT_FOUND)
            if title is not None:
                task.title = title
            if remind_at is not None:
                task.remind_at = remind_at
            task.updated_at = utc_now()
        return task

    async def delete(self, user_id: str, task_id: str) -> None:
        async with self.sessions.begin() as session:
            task = await session.get(Task, task_id)
            if task is None or task.user_id != user_id:
                raise AppError("TASK_NOT_FOUND", "待办不存在。", 404, ErrorCategory.NOT_FOUND)
            task.status = "deleted"
            task.updated_at = utc_now()

    async def claim_due(self, limit: int = 100) -> list[Task]:
        """Atomically claims due tasks with UPDATE ... RETURNING."""
        now = utc_now()
        candidate_ids = (
            select(Task.id)
            .where(
                Task.status == "pending",
                Task.remind_at.is_not(None),
                Task.remind_at <= now,
                Task.notified_at.is_(None),
            )
            .order_by(Task.remind_at.asc())
            .limit(limit)
            .scalar_subquery()
        )
        statement = (
            update(Task)
            .where(Task.id.in_(candidate_ids), Task.notified_at.is_(None))
            .values(notified_at=now, updated_at=now)
            .returning(Task)
        )
        async with self.sessions.begin() as session:
            result = await session.execute(statement)
            return list(result.scalars())
