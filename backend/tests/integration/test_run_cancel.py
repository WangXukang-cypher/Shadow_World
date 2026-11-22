import asyncio
from collections.abc import AsyncIterator

from app.llm.models import LLMEvent, LLMRequest, ResponseCompleted, TextDelta


class SlowProvider:
    name = "slow-test"

    async def create_response(self, request: LLMRequest):
        raise AssertionError("runtime should use stream_response")

    async def stream_response(self, request: LLMRequest) -> AsyncIterator[LLMEvent]:
        del request
        for text in ["这", "是", "一", "段", "慢", "回", "复"]:
            await asyncio.sleep(0.05)
            yield TextDelta(text=text)
        yield ResponseCompleted(finish_reason="stop")


def test_running_run_can_be_cancelled(app, client):
    app.state.runtime.provider = SlowProvider()
    conversation = client.post("/api/v1/conversations", json={}).json()
    run = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"content": "慢慢回答"},
    ).json()

    async def wait_until_running():
        for _ in range(100):
            item = await app.state.service.get_run(app.state.default_user_id, run["id"])
            if item.status == "running":
                return
            await asyncio.sleep(0.01)
        raise AssertionError("run did not start")

    asyncio.run(wait_until_running())
    response = client.post(f"/api/v1/runs/{run['id']}/cancel")
    assert response.status_code == 200

    async def wait_until_cancelled():
        for _ in range(100):
            item = await app.state.service.get_run(app.state.default_user_id, run["id"])
            if item.status == "cancelled":
                return item
            await asyncio.sleep(0.01)
        raise AssertionError("run was not cancelled")

    cancelled = asyncio.run(wait_until_cancelled())
    assert cancelled.cancel_requested_at is not None
    events = client.get(f"/api/v1/runs/{run['id']}/events").text
    assert "event: run.cancelled" in events
