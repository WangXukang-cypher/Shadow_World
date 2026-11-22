import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse

from app.api.dependencies import BrokerDep, ServiceDep, UserIdDep
from app.schemas.notifications import NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


def sse(event_id: int, event: str, data: dict) -> str:
    return f"id: {event_id}\nevent: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    service: ServiceDep,
    user_id: UserIdDep,
    after_id: int = 0,
):
    return await service.list_notifications(user_id, after_id)


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: int,
    service: ServiceDep,
    user_id: UserIdDep,
):
    await service.delete_notification(user_id, notification_id)


@router.delete("", status_code=204)
async def clear_notifications(
    service: ServiceDep,
    user_id: UserIdDep,
):
    await service.clear_notifications(user_id)


@router.get("/stream")
async def notification_stream(
    request: Request,
    service: ServiceDep,
    broker: BrokerDep,
    user_id: UserIdDep,
    last_event_id: Annotated[str | None, Header()] = None,
):
    after_id = int(last_event_id or 0)

    async def stream():
        nonlocal after_id
        for item in await service.list_notifications(user_id, after_id):
            after_id = item.id
            payload = NotificationRead.model_validate(item).model_dump(mode="json")
            yield sse(item.id, item.type, payload)
        queue = broker.subscribe_notifications(user_id)
        try:
            while not await request.is_disconnected():
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15)
                    if item["id"] <= after_id:
                        continue
                    after_id = item["id"]
                    yield sse(item["id"], item["event"], item["data"])
                except TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            broker.unsubscribe_notifications(user_id, queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        # nginx 等反代见到此头会禁用响应缓冲，保证 SSE 实时推送
        headers={"X-Accel-Buffering": "no"},
    )
