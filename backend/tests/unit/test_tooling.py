import asyncio

import pytest

from app.application.services import DEFAULT_USER_ID
from app.core.errors import AppError
from app.tools import ToolContext, build_tooling


def test_registry_rejects_duplicate_tool():
    registry, _ = build_tooling()
    with pytest.raises(ValueError, match="duplicate tool"):
        registry.register(registry.get("create_memory"))


def test_executor_validates_arguments(app, client):
    del client
    registry, executor = build_tooling()
    context = ToolContext(
        user_id=DEFAULT_USER_ID,
        conversation_id="conversation",
        run_id="run",
        source_message_id="message",
        call_id="call",
        timezone="Asia/Shanghai",
        service=app.state.service,
    )

    async def scenario():
        with pytest.raises(AppError) as exc_info:
            await executor.execute(
                "create_memory", {"content": ""}, context, allowed={"create_memory"}
            )
        assert exc_info.value.code == "TOOL_ARGUMENT_INVALID"
        assert {item.name for item in registry.definitions()} == {
            "get_current_time",
            "create_memory",
            "list_memories",
            "update_memory",
            "delete_memory",
            "create_task",
            "list_tasks",
            "complete_task",
            "delete_task",
            "add_person",
            "list_people",
            "add_commitment",
            "list_skills",
            "manage_skill",
            "invoke_skill",
            "web_search",
        }

    asyncio.run(scenario())
