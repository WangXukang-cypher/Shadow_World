from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, update

from app.application.keyed_lock import KeyedLockPool
from app.core.errors import AppError, ErrorCategory
from app.infrastructure.db.models import AgentRun, RunEvent

from .base import ServiceBase, utc_now


class RunService(ServiceBase):
    def __init__(self, sessions):
        super().__init__(sessions)
        self.event_locks = KeyedLockPool()

    async def create(self, user_id: str, conversation_id: str, input_message_id: str) -> AgentRun:
        run = AgentRun(
            id=str(uuid.uuid4()),
            user_id=user_id,
            conversation_id=conversation_id,
            input_message_id=input_message_id,
            status="queued",
            route="",
            created_at=utc_now(),
        )
        async with self.sessions.begin() as session:
            await self.get_owned_conversation(session, user_id, conversation_id)
            session.add(run)
        return run

    async def get(self, user_id: str, run_id: str) -> AgentRun:
        async with self.sessions() as session:
            run = await session.get(AgentRun, run_id)
            if run is None or run.user_id != user_id:
                raise AppError("RUN_NOT_FOUND", "运行不存在。", 404, ErrorCategory.NOT_FOUND)
            return run

    async def set_status(
        self,
        run_id: str,
        status: str,
        route: str,
        output_message_id: str | None = None,
        error_code: str | None = None,
        model_name: str | None = None,
        iteration_count: int | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
    ) -> None:
        async with self.sessions.begin() as session:
            run = await session.get(AgentRun, run_id)
            if run is None:
                return
            run.status = status
            run.route = route
            run.output_message_id = output_message_id
            run.error_code = error_code
            if model_name is not None:
                run.model_name = model_name
            if iteration_count is not None:
                run.iteration_count = iteration_count
            if prompt_tokens is not None:
                run.prompt_tokens = prompt_tokens
            if completion_tokens is not None:
                run.completion_tokens = completion_tokens
            if status in {"completed", "failed", "cancelled"}:
                run.completed_at = utc_now()

    async def request_cancel(self, user_id: str, run_id: str) -> AgentRun:
        async with self.sessions.begin() as session:
            run = await session.get(AgentRun, run_id)
            if run is None or run.user_id != user_id:
                raise AppError("RUN_NOT_FOUND", "运行不存在。", 404, ErrorCategory.NOT_FOUND)
            if run.status in {"completed", "failed", "cancelled"}:
                return run
            run.cancel_requested_at = utc_now()
            return run

    async def is_cancel_requested(self, run_id: str) -> bool:
        async with self.sessions() as session:
            run = await session.get(AgentRun, run_id)
            return run is not None and run.cancel_requested_at is not None

    async def fail_stale_runs(self) -> int:
        """将所有非终态 run 标记为失败并记录数量。

        在服务启动时调用：进程重启后旧的 queued/running run 不可能还在执行，
        不清理会让客户端永远等不到终止事件（界面一直显示"思考中"）。
        """
        async with self.sessions.begin() as session:
            result = await session.execute(
                update(AgentRun)
                .where(AgentRun.status.in_(["queued", "running"]))
                .values(status="failed", error_code="RUN_STALE", completed_at=utc_now())
            )
            return result.rowcount or 0

    async def append_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> RunEvent:
        async with self.event_locks.hold(run_id):
            async with self.sessions.begin() as session:
                max_seq = await session.scalar(
                    select(func.max(RunEvent.seq)).where(RunEvent.run_id == run_id)
                )
                event = RunEvent(
                    run_id=run_id,
                    seq=(max_seq or 0) + 1,
                    event_type=event_type,
                    payload=payload,
                    created_at=utc_now(),
                )
                session.add(event)
                await session.flush()
                event_id = event.id
            event.id = event_id
            return event

    async def list_events(self, user_id: str, run_id: str, after_seq: int = 0) -> list[RunEvent]:
        await self.get(user_id, run_id)
        async with self.sessions() as session:
            return list(
                await session.scalars(
                    select(RunEvent)
                    .where(RunEvent.run_id == run_id, RunEvent.seq > after_seq)
                    .order_by(RunEvent.seq.asc())
                )
            )
