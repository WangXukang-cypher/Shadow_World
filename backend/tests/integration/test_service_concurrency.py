import asyncio

from app.application.services import DEFAULT_USER_ID


def test_concurrent_messages_keep_strict_sequence(app, client):
    conversation = client.post("/api/v1/conversations", json={}).json()
    service = app.state.service

    async def add_messages():
        await asyncio.gather(
            *[
                service.add_message(DEFAULT_USER_ID, conversation["id"], "user", f"message-{index}")
                for index in range(10)
            ]
        )
        _, messages = await service.get_conversation_with_messages(
            DEFAULT_USER_ID, conversation["id"]
        )
        return messages

    messages = asyncio.run(add_messages())
    assert [message.seq for message in messages] == list(range(1, 11))
