import asyncio

from app.application.services import DEFAULT_USER_ID


def _seed_conversation_with_references(service):
    """创建带消息引用（记忆/待办）的会话：模拟群聊中人格调用过 create_memory/create_task。"""

    async def scenario():
        conv = await service.create_conversation(DEFAULT_USER_ID, "测试多人格的群聊")
        msg = await service.add_message(DEFAULT_USER_ID, conv.id, "user", "记住我喜欢吃火锅")
        await service.create_memory(
            DEFAULT_USER_ID, "用户喜欢吃火锅", source_message_id=msg.id
        )
        await service.create_task(
            DEFAULT_USER_ID, "提醒吃火锅", source_message_id=msg.id
        )
        return conv

    return asyncio.run(scenario())


def test_delete_conversation_with_memory_and_task_references(app, client):
    """消息被记忆/待办的 source_message_id 引用时，删除会话应成功，记忆和待办保留。"""
    service = app.state.service
    conv = _seed_conversation_with_references(service)

    # 记忆和待办已创建
    memories = asyncio.run(service.list_memories(DEFAULT_USER_ID))
    tasks = asyncio.run(service.list_tasks(DEFAULT_USER_ID))
    assert any(m.content == "用户喜欢吃火锅" for m in memories)
    assert any(t.title == "提醒吃火锅" for t in tasks)

    # 删除会话：修复前会因外键约束失败（500），修复后应为 204
    response = client.delete(f"/api/v1/conversations/{conv.id}")
    assert response.status_code == 204, (
        f"删除失败: {response.status_code} {response.text}"
    )

    # 会话已删除
    assert client.get(f"/api/v1/conversations/{conv.id}").status_code == 404

    # 记忆和待办保留，但来源引用被清空
    memories = asyncio.run(service.list_memories(DEFAULT_USER_ID))
    tasks = asyncio.run(service.list_tasks(DEFAULT_USER_ID))
    memory = next(m for m in memories if m.content == "用户喜欢吃火锅")
    task = next(t for t in tasks if t.title == "提醒吃火锅")
    assert memory.source_message_id is None
    assert task.source_message_id is None
