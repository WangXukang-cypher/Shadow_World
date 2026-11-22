from __future__ import annotations

from app.infrastructure.db.models import User

from .base import DEFAULT_USER_ID, ServiceBase, utc_now


class UserService(ServiceBase):
    async def ensure_default_user(self, timezone: str) -> None:
        async with self.sessions.begin() as session:
            user = await session.get(User, DEFAULT_USER_ID)
            if user is None:
                session.add(
                    User(
                        id=DEFAULT_USER_ID,
                        display_name="本地用户",
                        timezone=timezone,
                        created_at=utc_now(),
                    )
                )

    async def ensure_user(self, user_id: str, timezone: str) -> None:
        """幂等创建匿名访客用户（display_name 为空表示尚未完成引导）。"""
        async with self.sessions.begin() as session:
            if await session.get(User, user_id) is None:
                session.add(
                    User(
                        id=user_id,
                        display_name="",
                        timezone=timezone,
                        created_at=utc_now(),
                    )
                )

    async def exists(self, user_id: str) -> bool:
        async with self.sessions() as session:
            return await session.get(User, user_id) is not None

    async def get(self, user_id: str) -> User | None:
        async with self.sessions() as session:
            return await session.get(User, user_id)

    async def update_display_name(self, user_id: str, display_name: str) -> User:
        from app.core.errors import AppError, ErrorCategory

        async with self.sessions.begin() as session:
            user = await session.get(User, user_id)
            if user is None:
                raise AppError(
                    "USER_NOT_FOUND", "用户不存在。", 404, ErrorCategory.NOT_FOUND
                )
            user.display_name = display_name
            return user
