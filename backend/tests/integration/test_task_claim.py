import asyncio
from datetime import UTC, datetime, timedelta

from app.application.services import DEFAULT_USER_ID


def test_due_task_claim_is_atomic(app, client):
    service = app.state.service

    async def scenario():
        await service.create_task(
            DEFAULT_USER_ID,
            "due task",
            remind_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        first, second = await asyncio.gather(service.claim_due_tasks(), service.claim_due_tasks())
        return first, second

    first, second = asyncio.run(scenario())
    claimed_ids = [task.id for task in first] + [task.id for task in second]
    assert len(claimed_ids) == 1
    assert len(set(claimed_ids)) == 1
