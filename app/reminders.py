import asyncio
from collections.abc import Awaitable, Callable

from .async_db import AsyncDatabase


class ReminderWorker:
    def __init__(
        self, db: AsyncDatabase, interval_seconds: float, publish: Callable[[dict], Awaitable[None]]
    ):
        self.db = db
        self.interval_seconds = interval_seconds
        self.publish = publish
        self._stopping = asyncio.Event()

    async def run(self) -> None:
        while not self._stopping.is_set():
            for task in await self.db.due_tasks():
                notification = await self.db.create_notification(
                    task["user_id"],
                    "task.reminder",
                    {"task_id": task["id"], "title": task["title"]},
                )
                await self.db.mark_task_notified(task["id"])
                await self.publish(notification)
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=self.interval_seconds)
            except TimeoutError:
                pass

    def stop(self) -> None:
        self._stopping.set()
