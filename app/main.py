from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from .async_db import AsyncDatabase
from .config import Settings, load_settings, validate_settings
from .db import DEFAULT_USER_ID, Database
from .mock_provider import MockLLMProvider
from .rate_limit import RateLimitExceeded, RunLimiter
from .reminders import ReminderWorker
from .runtime import AgentRuntime


class MessageInput(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class MemoryInput(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    type: str = "fact"
    subject: str = "我"


class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    remind_at: str | None = None


def _sse(event: str, data: dict[str, Any], event_id: int | None = None) -> str:
    prefix = f"id: {event_id}\n" if event_id is not None else ""
    return f"{prefix}event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or load_settings()
    validate_settings(cfg)
    sync_db = Database(cfg.database_path)
    sync_db.initialize()
    db = AsyncDatabase(sync_db)
    limiter = RunLimiter(
        cfg.max_active_runs_per_user, cfg.max_global_runs, cfg.message_rate_limit_per_minute
    )
    runtime = AgentRuntime(db, MockLLMProvider(), limiter, cfg.timezone)
    notification_queues: dict[str, set] = {}

    async def publish(notification: dict) -> None:
        for queue in list(notification_queues.get(DEFAULT_USER_ID, set())):
            await queue.put(notification)

    worker = ReminderWorker(db, cfg.reminder_poll_seconds, publish)

    async def limiter_cleanup_loop() -> None:
        while True:
            await asyncio.sleep(60)
            await limiter.cleanup_expired()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        worker_task = asyncio.create_task(worker.run())
        limiter_task = asyncio.create_task(limiter_cleanup_loop())
        try:
            yield
        finally:
            worker.stop()
            limiter_task.cancel()
            await worker_task
            try:
                await limiter_task
            except asyncio.CancelledError:
                pass

    app = FastAPI(title="Memento Assistant", version="0.1.0", lifespan=lifespan)
    app.state.db = db
    app.state.sync_db = sync_db
    app.state.runtime = runtime

    @app.get("/")
    async def index():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "provider": cfg.llm_provider, "mode": "mvp"}

    @app.post("/api/v1/conversations")
    async def create_conversation():
        return await db.create_conversation(DEFAULT_USER_ID)

    @app.get("/api/v1/conversations")
    async def list_conversations():
        return await db.list_conversations(DEFAULT_USER_ID)

    @app.get("/api/v1/conversations/{conversation_id}")
    async def get_conversation(conversation_id: str):
        try:
            conversation = await db.get_conversation(conversation_id, DEFAULT_USER_ID)
            conversation["messages"] = await db.list_messages(conversation_id, DEFAULT_USER_ID)
            return conversation
        except KeyError as exc:
            raise HTTPException(404, "conversation not found") from exc

    @app.post("/api/v1/conversations/{conversation_id}/messages", status_code=202)
    async def send_message(conversation_id: str, body: MessageInput):
        try:
            return await runtime.start(conversation_id, body.content, DEFAULT_USER_ID)
        except KeyError as exc:
            raise HTTPException(404, "conversation not found") from exc
        except RateLimitExceeded as exc:
            raise HTTPException(429, str(exc)) from exc

    @app.get("/api/v1/runs/{run_id}/events")
    async def run_events(run_id: str):
        async def stream():
            try:
                async for item in runtime.events(run_id):
                    yield _sse(item["event"], item["data"])
            except KeyError:
                yield _sse("run.failed", {"code": "RUN_NOT_FOUND", "message": "运行不存在。"})

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/v1/memories")
    async def list_memories():
        return await db.list_memories(DEFAULT_USER_ID)

    @app.post("/api/v1/memories")
    async def create_memory(body: MemoryInput):
        return await db.create_memory(DEFAULT_USER_ID, body.content, body.type, body.subject)

    @app.get("/api/v1/tasks")
    async def list_tasks():
        return await db.list_tasks(DEFAULT_USER_ID)

    @app.post("/api/v1/tasks")
    async def create_task(body: TaskInput):
        return await db.create_task(DEFAULT_USER_ID, body.title, body.remind_at)

    @app.get("/api/v1/notifications")
    async def list_notifications(after_id: int = 0):
        return await db.list_notifications(DEFAULT_USER_ID, after_id)

    @app.get("/api/v1/notifications/stream")
    async def notification_stream(
        request: Request, last_event_id: str | None = Header(default=None)
    ):
        queue: asyncio.Queue = asyncio.Queue()
        notification_queues.setdefault(DEFAULT_USER_ID, set()).add(queue)
        after_id = int(last_event_id or 0)

        async def stream():
            try:
                for item in await db.list_notifications(DEFAULT_USER_ID, after_id):
                    yield _sse(item["type"], item, item["id"])
                while not await request.is_disconnected():
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=15)
                        yield _sse(item["type"], item, item["id"])
                    except TimeoutError:
                        yield ": heartbeat\n\n"
            finally:
                notification_queues[DEFAULT_USER_ID].discard(queue)

        return StreamingResponse(stream(), media_type="text/event-stream")

    return app


app = create_app()
