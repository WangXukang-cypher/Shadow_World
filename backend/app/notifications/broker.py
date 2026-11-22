import asyncio
from collections import defaultdict
from typing import Any


class EventBroker:
    def __init__(self):
        self._run_subscribers: defaultdict[str, set[asyncio.Queue]] = defaultdict(set)
        self._notification_subscribers: defaultdict[str, set[asyncio.Queue]] = defaultdict(set)

    async def publish_run(self, run_id: str, event: dict[str, Any]) -> None:
        for queue in list(self._run_subscribers.get(run_id, set())):
            await queue.put(event)

    async def publish_notification(self, user_id: str, event: dict[str, Any]) -> None:
        for queue in list(self._notification_subscribers.get(user_id, set())):
            await queue.put(event)

    def subscribe_run(self, run_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._run_subscribers[run_id].add(queue)
        return queue

    def unsubscribe_run(self, run_id: str, queue: asyncio.Queue) -> None:
        subscribers = self._run_subscribers.get(run_id)
        if subscribers is None:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._run_subscribers.pop(run_id, None)

    def subscribe_notifications(self, user_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._notification_subscribers[user_id].add(queue)
        return queue

    def unsubscribe_notifications(self, user_id: str, queue: asyncio.Queue) -> None:
        subscribers = self._notification_subscribers.get(user_id)
        if subscribers is None:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._notification_subscribers.pop(user_id, None)
