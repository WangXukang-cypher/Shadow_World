from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.errors import AppError, ErrorCategory
from app.infrastructure.db.models import Skill

from .base import ServiceBase, utc_now


class SkillService(ServiceBase):
    async def create(
        self,
        user_id: str,
        name: str,
        description: str,
        system_prompt: str,
    ) -> Skill:
        async with self.sessions() as session:
            now = utc_now()
            skill = Skill(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=name,
                description=description,
                system_prompt=system_prompt,
                status="active",
                created_at=now,
                updated_at=now,
            )
            session.add(skill)
            await session.commit()
            await session.refresh(skill)
            return skill

    async def list(self, user_id: str) -> list[Skill]:
        async with self.sessions() as session:
            result = await session.execute(
                select(Skill)
                .where(Skill.user_id == user_id, Skill.status == "active")
                .order_by(Skill.created_at.desc())
            )
            return list(result.scalars().all())

    async def get(self, user_id: str, skill_id: str) -> Skill:
        async with self.sessions() as session:
            skill = await session.get(Skill, skill_id)
            if skill is None or skill.user_id != user_id or skill.status != "active":
                raise AppError(
                    "SKILL_NOT_FOUND", "技能不存在。", 404, ErrorCategory.NOT_FOUND
                )
            return skill

    async def get_by_name(self, user_id: str, name: str) -> Skill | None:
        async with self.sessions() as session:
            result = await session.execute(
                select(Skill).where(
                    Skill.user_id == user_id,
                    Skill.name == name,
                    Skill.status == "active",
                )
            )
            return result.scalar_one_or_none()

    async def update(
        self,
        user_id: str,
        skill_id: str,
        name: str | None = None,
        description: str | None = None,
        system_prompt: str | None = None,
    ) -> Skill:
        async with self.sessions() as session:
            skill = await session.get(Skill, skill_id)
            if skill is None or skill.user_id != user_id or skill.status != "active":
                raise AppError(
                    "SKILL_NOT_FOUND", "技能不存在。", 404, ErrorCategory.NOT_FOUND
                )
            if name is not None:
                skill.name = name
            if description is not None:
                skill.description = description
            if system_prompt is not None:
                skill.system_prompt = system_prompt
            skill.updated_at = utc_now()
            await session.commit()
            await session.refresh(skill)
            return skill

    async def delete(self, user_id: str, skill_id: str) -> None:
        async with self.sessions() as session:
            skill = await session.get(Skill, skill_id)
            if skill is None or skill.user_id != user_id:
                raise AppError(
                    "SKILL_NOT_FOUND", "技能不存在。", 404, ErrorCategory.NOT_FOUND
                )
            skill.status = "archived"
            skill.updated_at = utc_now()
            await session.commit()
