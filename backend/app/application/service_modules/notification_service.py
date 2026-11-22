from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select

from app.core.errors import AppError, ErrorCategory
from app.infrastructure.db.models import Notification

from .base import ServiceBase, utc_now


class NotificationService(ServiceBase):
    async def create(
        self, user_id: str, notification_type: str, payload: dict[str, Any]
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            payload=payload,
            created_at=utc_now(),
        )
        async with self.sessions.begin() as session:
            session.add(notification)
            await session.flush()
            notification_id = notification.id
        notification.id = notification_id
        return notification

    async def list(self, user_id: str, after_id: int = 0, limit: int = 100) -> list[Notification]:
        async with self.sessions() as session:
            return list(
                await session.scalars(
                    select(Notification)
                    .where(Notification.user_id == user_id, Notification.id > after_id)
                    .order_by(Notification.id.asc())
                    .limit(limit)
                )
            )

    async def delete(self, user_id: str, notification_id: int) -> None:
        async with self.sessions.begin() as session:
            result = await session.execute(
                delete(Notification).where(
                    Notification.user_id == user_id,
                    Notification.id == notification_id,
                )
            )
            if result.rowcount == 0:
                raise AppError(
                    "NOTIFICATION_NOT_FOUND",
                    "通知不存在。",
                    404,
                    ErrorCategory.NOT_FOUND,
                )

    async def delete_all(self, user_id: str) -> None:
        async with self.sessions.begin() as session:
            await session.execute(delete(Notification).where(Notification.user_id == user_id))
