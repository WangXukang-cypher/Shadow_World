import asyncio
import logging

from app.application.services import ApplicationService
from app.notifications.broker import EventBroker

logger = logging.getLogger(__name__)


class ReminderWorker:
    def __init__(
        self,
        service: ApplicationService,
        broker: EventBroker,
        interval_seconds: float,
    ):
        self.service = service
        self.broker = broker
        self.interval_seconds = interval_seconds
        self._stopping = asyncio.Event()

    async def run(self) -> None:
        while not self._stopping.is_set():
            try:
                for task in await self.service.claim_due_tasks():
                    notification = await self.service.create_notification(
                        task.user_id,
                        "task.reminder",
                        {"task_id": task.id, "title": task.title},
                    )
                    await self.broker.publish_notification(
                        task.user_id,
                        {
                            "id": notification.id,
                            "event": notification.type,
                            "data": {
                                "id": notification.id,
                                "type": notification.type,
                                "payload": notification.payload,
                                "created_at": notification.created_at.isoformat(),
                            },
                        },
                    )
            except Exception:
                logger.exception("reminder worker iteration failed")
            try:
                await asyncio.wait_for(self._stopping.wait(), self.interval_seconds)
            except TimeoutError:
                pass

    def stop(self) -> None:
        self._stopping.set()
