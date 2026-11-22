from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.errors import AppError, ErrorCategory
from app.infrastructure.db.models import Person, SocialCommitment

from .base import ServiceBase, utc_now


class PeopleService(ServiceBase):
    async def add_or_update(
        self,
        user_id: str,
        name: str,
        relationship: str = "朋友",
        nickname: str | None = None,
        traits: str | None = None,
        birthday: str | None = None,
        notes: str | None = None,
    ) -> Person:
        async with self.sessions.begin() as session:
            existing = await session.scalar(
                select(Person).where(Person.user_id == user_id, Person.name == name)
            )
            if existing:
                if nickname is not None:
                    existing.nickname = nickname
                if traits is not None:
                    existing.traits = traits
                if birthday is not None:
                    existing.birthday = birthday
                if notes is not None:
                    existing.notes = notes
                if relationship:
                    existing.relationship = relationship
                existing.updated_at = utc_now()
                return existing
            now = utc_now()
            person = Person(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=name,
                nickname=nickname,
                relationship=relationship,
                traits=traits,
                birthday=birthday,
                notes=notes,
                mention_count=0,
                created_at=now,
                updated_at=now,
            )
            session.add(person)
            return person

    async def list(self, user_id: str) -> list[Person]:
        async with self.sessions() as session:
            return list(
                await session.scalars(
                    select(Person)
                    .where(Person.user_id == user_id)
                    .order_by(Person.mention_count.desc(), Person.updated_at.desc())
                )
            )

    async def get_by_name(self, user_id: str, name: str) -> Person | None:
        async with self.sessions() as session:
            return await session.scalar(
                select(Person).where(Person.user_id == user_id, Person.name == name)
            )

    async def get(self, user_id: str, person_id: str) -> Person:
        async with self.sessions() as session:
            person = await session.get(Person, person_id)
            if person is None or person.user_id != user_id:
                raise AppError("PERSON_NOT_FOUND", "人物不存在。", 404, ErrorCategory.NOT_FOUND)
            return person

    async def update(
        self,
        user_id: str,
        person_id: str,
        name: str | None = None,
        relationship: str | None = None,
        nickname: str | None = None,
        traits: str | None = None,
        birthday: str | None = None,
        notes: str | None = None,
    ) -> Person:
        async with self.sessions.begin() as session:
            person = await session.get(Person, person_id)
            if person is None or person.user_id != user_id:
                raise AppError("PERSON_NOT_FOUND", "人物不存在。", 404, ErrorCategory.NOT_FOUND)
            if name is not None:
                person.name = name
            if relationship is not None:
                person.relationship = relationship
            if nickname is not None:
                person.nickname = nickname
            if traits is not None:
                person.traits = traits
            if birthday is not None:
                person.birthday = birthday
            if notes is not None:
                person.notes = notes
            person.updated_at = utc_now()
        return person

    async def delete(self, user_id: str, person_id: str) -> None:
        async with self.sessions.begin() as session:
            person = await session.get(Person, person_id)
            if person is None or person.user_id != user_id:
                raise AppError("PERSON_NOT_FOUND", "人物不存在。", 404, ErrorCategory.NOT_FOUND)
            await session.delete(person)

    async def record_mention(self, user_id: str, name: str) -> None:
        async with self.sessions.begin() as session:
            person = await session.scalar(
                select(Person).where(Person.user_id == user_id, Person.name == name)
            )
            if person:
                person.mention_count += 1
                person.last_mentioned_at = utc_now()

    async def add_commitment(
        self, user_id: str, person_id: str, content: str, source_message_id: str | None = None
    ) -> SocialCommitment:
        async with self.sessions.begin() as session:
            commitment = SocialCommitment(
                id=str(uuid.uuid4()),
                user_id=user_id,
                person_id=person_id,
                content=content,
                status="pending",
                source_message_id=source_message_id,
                created_at=utc_now(),
            )
            session.add(commitment)
        return commitment

    async def list_commitments(self, user_id: str) -> list[SocialCommitment]:
        async with self.sessions() as session:
            return list(
                await session.scalars(
                    select(SocialCommitment)
                    .where(SocialCommitment.user_id == user_id, SocialCommitment.status == "pending")
                    .order_by(SocialCommitment.created_at.desc())
                )
            )

    async def complete_commitment(self, user_id: str, commitment_id: str) -> SocialCommitment:
        async with self.sessions.begin() as session:
            c = await session.get(SocialCommitment, commitment_id)
            if c is None or c.user_id != user_id:
                raise AppError("COMMITMENT_NOT_FOUND", "承诺不存在。", 404, ErrorCategory.NOT_FOUND)
            c.status = "completed"
            c.completed_at = utc_now()
        return c

    async def get_social_graph(self, user_id: str) -> dict:
        async with self.sessions() as session:
            people = list(
                await session.scalars(
                    select(Person).where(Person.user_id == user_id)
                )
            )
            commitments = list(
                await session.scalars(
                    select(SocialCommitment).where(
                        SocialCommitment.user_id == user_id,
                        SocialCommitment.status == "pending",
                    )
                )
            )
        nodes = [
            {
                "id": p.id,
                "name": p.name,
                "nickname": p.nickname,
                "relationship": p.relationship,
                "traits": p.traits.split(",") if p.traits else [],
                "birthday": p.birthday,
                "mention_count": p.mention_count,
                "notes": p.notes,
            }
            for p in people
        ]
        pending_commitments = [
            {
                "id": c.id,
                "person_id": c.person_id,
                "content": c.content,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in commitments
        ]
        return {"nodes": nodes, "commitments": pending_commitments}
