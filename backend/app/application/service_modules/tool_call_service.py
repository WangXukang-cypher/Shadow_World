from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.infrastructure.db.models import ToolCallRecord

from .base import ServiceBase, utc_now


class ToolCallService(ServiceBase):
    async def get_by_idempotency_key(self, key: str) -> ToolCallRecord | None:
        async with self.sessions() as session:
            return await session.scalar(
                select(ToolCallRecord).where(ToolCallRecord.idempotency_key == key)
            )

    async def create(
        self,
        run_id: str,
        call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        side_effect: str,
        idempotency_key: str,
    ) -> ToolCallRecord:
        record = ToolCallRecord(
            id=str(uuid.uuid4()),
            run_id=run_id,
            call_id=call_id,
            tool_name=tool_name,
            arguments=arguments,
            status="running",
            side_effect=side_effect,
            idempotency_key=idempotency_key,
            created_at=utc_now(),
        )
        async with self.sessions.begin() as session:
            session.add(record)
        return record

    async def complete(
        self,
        record_id: str,
        result: dict[str, Any],
        model_content: str,
        latency_ms: int,
    ) -> None:
        async with self.sessions.begin() as session:
            record = await session.get(ToolCallRecord, record_id)
            if record is None:
                return
            record.result = result
            record.model_content = model_content
            record.status = "completed"
            record.latency_ms = latency_ms
            record.completed_at = utc_now()

    async def fail(self, record_id: str, error_code: str, latency_ms: int) -> None:
        async with self.sessions.begin() as session:
            record = await session.get(ToolCallRecord, record_id)
            if record is None:
                return
            record.status = "failed"
            record.error_code = error_code
            record.latency_ms = latency_ms
            record.completed_at = utc_now()

    async def list_for_run(self, run_id: str) -> list[ToolCallRecord]:
        async with self.sessions() as session:
            return list(
                await session.scalars(
                    select(ToolCallRecord)
                    .where(ToolCallRecord.run_id == run_id)
                    .order_by(ToolCallRecord.created_at.asc())
                )
            )
