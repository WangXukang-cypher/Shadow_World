import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import asdict
from typing import Any

from .async_db import AsyncDatabase
from .db import DEFAULT_USER_ID
from .mock_provider import MockLLMProvider
from .rate_limit import RunLimiter
from .time_parser import parse_mock_reminder

logger = logging.getLogger(__name__)


class AgentRuntime:
    def __init__(
        self, db: AsyncDatabase, provider: MockLLMProvider, limiter: RunLimiter, timezone_name: str
    ):
        self.db = db
        self.provider = provider
        self.limiter = limiter
        self.timezone_name = timezone_name
        self._queues: dict[str, asyncio.Queue] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._cleanup_handles: dict[str, asyncio.TimerHandle] = {}

    async def start(
        self, conversation_id: str, text: str, user_id: str = DEFAULT_USER_ID
    ) -> dict[str, Any]:
        await self.limiter.reserve(user_id)
        try:
            await self.db.add_message(conversation_id, user_id, "user", text)
            run = await self.db.create_run(user_id, conversation_id)
            queue: asyncio.Queue = asyncio.Queue()
            self._queues[run["id"]] = queue
            task = asyncio.create_task(
                self._execute(run["id"], conversation_id, text, user_id, queue)
            )
            self._tasks[run["id"]] = task
            task.add_done_callback(lambda _task, run_id=run["id"]: self._tasks.pop(run_id, None))
            return run
        except Exception:
            await self.limiter.release(user_id, global_acquired=False)
            raise

    async def _execute(
        self, run_id: str, conversation_id: str, text: str, user_id: str, queue: asyncio.Queue
    ) -> None:
        route = "chat"
        global_acquired = False
        try:
            await self.limiter.acquire_global()
            global_acquired = True
            await queue.put({"event": "run.started", "data": {"run_id": run_id}})
            decision = self.provider.decide(text)
            route = decision.route
            await queue.put(
                {"event": "agent.status", "data": {"route": route, "decision": asdict(decision)}}
            )
            reply = decision.reply
            if route == "create_memory":
                await queue.put({"event": "tool.started", "data": {"tool": "create_memory"}})
                memory = await self.db.create_memory(user_id, decision.argument or "")
                await queue.put({"event": "memory.saved", "data": memory})
            elif route == "list_memories":
                memories = await self.db.list_memories(user_id)
                reply = (
                    "我还没有保存长期记忆。"
                    if not memories
                    else "我记得：\n" + "\n".join(f"- {item['content']}" for item in memories)
                )
            elif route == "create_task":
                await queue.put({"event": "tool.started", "data": {"tool": "create_task"}})
                remind_at = parse_mock_reminder(decision.argument or "", self.timezone_name)
                task = await self.db.create_task(user_id, decision.argument or "", remind_at)
                await queue.put(
                    {"event": "tool.finished", "data": {"tool": "create_task", "result": task}}
                )
            elif route == "list_tasks":
                tasks = await self.db.list_tasks(user_id)
                reply = (
                    "当前没有未完成待办。"
                    if not tasks
                    else "你的待办：\n" + "\n".join(f"- {item['title']}" for item in tasks)
                )

            for chunk in self._chunks(reply):
                await queue.put({"event": "assistant.delta", "data": {"text": chunk}})
                await asyncio.sleep(0.02)
            message = await self.db.add_message(conversation_id, user_id, "assistant", reply)
            await self.db.finish_run(run_id, "completed", route)
            await queue.put(
                {"event": "run.completed", "data": {"message": message, "route": route}}
            )
        except Exception as exc:
            logger.exception(
                "agent run failed: run_id=%s route=%s error=%s", run_id, route, type(exc).__name__
            )
            await self.db.finish_run(run_id, "failed", route, "RUN_FAILED")
            await queue.put(
                {
                    "event": "run.failed",
                    "data": {"code": "RUN_FAILED", "message": "处理失败，请稍后重试。"},
                }
            )
        finally:
            await self.limiter.release(user_id, global_acquired=global_acquired)
            loop = asyncio.get_running_loop()
            self._cleanup_handles[run_id] = loop.call_later(300, self._cleanup_run, run_id)
            await queue.put(None)

    async def events(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        queue = self._queues.get(run_id)
        if queue is None:
            raise KeyError("run not found")
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            self._cleanup_run(run_id)

    def _cleanup_run(self, run_id: str) -> None:
        self._queues.pop(run_id, None)
        self._tasks.pop(run_id, None)
        handle = self._cleanup_handles.pop(run_id, None)
        if handle is not None and not handle.cancelled():
            handle.cancel()

    @staticmethod
    def _chunks(text: str, size: int = 8):
        for start in range(0, len(text), size):
            yield text[start : start + size]
