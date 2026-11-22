from __future__ import annotations

from app.infrastructure.db.models import UserLLMSetting

from .base import ServiceBase, utc_now


class UserLLMService(ServiceBase):
    """用户私有的模型服务配置（每个用户自己的 API Key）。"""

    async def get(self, user_id: str) -> UserLLMSetting | None:
        async with self.sessions() as session:
            return await session.get(UserLLMSetting, user_id)

    async def upsert(
        self,
        user_id: str,
        provider: str,
        base_url: str,
        api_key: str,
        model: str,
    ) -> UserLLMSetting:
        """保存用户配置；api_key 为空表示沿用现有 Key。"""
        async with self.sessions.begin() as session:
            setting = await session.get(UserLLMSetting, user_id)
            if setting is None:
                setting = UserLLMSetting(
                    user_id=user_id,
                    provider=provider,
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                    updated_at=utc_now(),
                )
                session.add(setting)
            else:
                setting.provider = provider
                setting.base_url = base_url
                setting.model = model
                setting.updated_at = utc_now()
                if api_key:
                    setting.api_key = api_key
            return setting
