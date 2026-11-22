import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse

from app.api.dependencies import BrokerDep, RuntimeDep, ServiceDep, UserIdDep
from app.schemas.runs import RunCancelResponse, RunDetail, ToolCallRead

router = APIRouter(prefix="/runs", tags=["runs"])
TERMINAL_EVENTS = {"run.completed", "run.failed", "run.cancelled"}
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def sse(event_id: int, event: str, data: dict) -> str:
    return f"id: {event_id}\nevent: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/{run_id}", response_model=RunDetail)
async def get_run(
    run_id: str,
    service: ServiceDep,
    user_id: UserIdDep,
):
    run = await service.get_run(user_id, run_id)
    tool_calls = await service.list_tool_calls(run_id)
    return RunDetail(
        id=run.id,
        conversation_id=run.conversation_id,
        status=run.status,
        route=run.route,
        model_name=run.model_name,
        iteration_count=run.iteration_count,
        prompt_tokens=run.prompt_tokens,
        completion_tokens=run.completion_tokens,
        error_code=run.error_code,
        cancel_requested_at=run.cancel_requested_at,
        created_at=run.created_at,
        completed_at=run.completed_at,
        tool_calls=[
            ToolCallRead(
                id=item.id,
                call_id=item.call_id,
                tool_name=item.tool_name,
                status=item.status,
                side_effect=item.side_effect,
                latency_ms=item.latency_ms,
                error_code=item.error_code,
                result_preview=item.result,
                created_at=item.created_at,
                completed_at=item.completed_at,
            )
            for item in tool_calls
        ],
    )


@router.post("/{run_id}/cancel", response_model=RunCancelResponse)
async def cancel_run(
    run_id: str,
    runtime: RuntimeDep,
    user_id: UserIdDep,
):
    return await runtime.cancel(run_id, user_id)


@router.get("/{run_id}/events")
async def run_events(
    run_id: str,
    request: Request,
    service: ServiceDep,
    broker: BrokerDep,
    runtime: RuntimeDep,
    user_id: UserIdDep,
    last_event_id: Annotated[str | None, Header()] = None,
):
    after_seq = int(last_event_id or 0)

    # 自愈：run 在 DB 中非终态，但当前进程已没有对应任务（典型于后端重启）。
    # 此时不会有任何新事件产生，客户端会永远停在"思考中"，
    # 因此直接标记失败并补发终止事件，让界面立即恢复。
    run = await service.get_run(user_id, run_id)
    if run.status not in TERMINAL_STATUSES and not runtime.is_run_active(run_id):
        await service.set_run_status(
            run_id, "failed", run.route, error_code="RUN_STALE"
        )
        await service.append_run_event(
            run_id,
            "run.failed",
            {"code": "RUN_STALE", "message": "运行被中断（服务重启），请重试。"},
        )

    async def stream():
        nonlocal after_seq
        queue = broker.subscribe_run(run_id)
        try:
            run = await service.get_run(user_id, run_id)
            is_terminal = run.status in TERMINAL_STATUSES
            is_active = runtime.is_run_active(run_id)
            # An active task can commit its final status before persisting the terminal event.
            # Check the full history in that window so reconnects can also detect prior delivery.
            history_after = 0 if is_terminal and is_active else after_seq
            history = await service.list_run_events(user_id, run_id, history_after)
            for item in history:
                if item.seq > after_seq:
                    after_seq = item.seq
                    yield sse(item.seq, item.event_type, item.payload)
            if (is_terminal and not is_active) or any(
                item.event_type in TERMINAL_EVENTS for item in history
            ):
                return
            while not await request.is_disconnected():
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15)
                    if item["id"] <= after_seq:
                        continue
                    after_seq = item["id"]
                    yield sse(item["id"], item["event"], item["data"])
                    if item["event"] in TERMINAL_EVENTS:
                        return
                except TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            broker.unsubscribe_run(run_id, queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        # nginx 等反代见到此头会禁用响应缓冲，保证 SSE 实时推送
        headers={"X-Accel-Buffering": "no"},
    )
