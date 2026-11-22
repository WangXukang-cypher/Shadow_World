import asyncio

from app.application.services import DEFAULT_USER_ID
from app.tools import ToolContext, build_tooling


def test_write_tool_reuses_completed_result_within_same_user_request(app, client):
    conversation = client.post("/api/v1/conversations", json={}).json()
    service = app.state.service
    registry, executor = build_tooling()

    async def scenario():
        source = await service.add_message(
            DEFAULT_USER_ID, conversation["id"], "user", "记住我喜欢川菜"
        )
        run = await service.create_run(DEFAULT_USER_ID, conversation["id"], source.id)
        context = ToolContext(
            user_id=DEFAULT_USER_ID,
            conversation_id=conversation["id"],
            run_id=run.id,
            source_message_id=source.id,
            call_id="call-1",
            timezone="Asia/Shanghai",
            service=service,
        )
        first = await executor.execute(
            "create_memory", {"content": "我喜欢川菜"}, context, allowed={"create_memory"}
        )
        context.call_id = "call-2"
        second = await executor.execute(
            "create_memory", {"content": "我喜欢川菜"}, context, allowed={"create_memory"}
        )
        records = await service.list_tool_calls(run.id)
        memories = await service.list_memories(DEFAULT_USER_ID)
        return first, second, records, memories

    first, second, records, memories = asyncio.run(scenario())
    assert first.output == second.output
    assert len(records) == 1
    assert len(memories) == 1
    assert {item.name for item in registry.definitions()} >= {"create_memory"}
