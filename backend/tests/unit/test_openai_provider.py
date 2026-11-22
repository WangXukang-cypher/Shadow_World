import asyncio
import json

import httpx

from app.llm.models import LLMRequest, ModelMessage, ToolDefinition
from app.llm.openai_compatible import OpenAICompatibleProvider


def test_openai_provider_parses_non_stream_tool_calls():
    async def handler(request: httpx.Request):
        payload = json.loads(request.content)
        assert payload["tools"][0]["function"]["name"] == "create_memory"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {
                                        "name": "create_memory",
                                        "arguments": '{"content":"喜欢川菜"}',
                                    },
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3},
            },
        )

    async def scenario():
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        provider = OpenAICompatibleProvider(
            "https://example.test/v1", "secret", "model", client=client
        )
        response = await provider.create_response(
            LLMRequest(
                messages=[ModelMessage(role="user", content="记住我喜欢川菜")],
                tools=[
                    ToolDefinition(
                        name="create_memory",
                        description="memory",
                        parameters={"type": "object"},
                    )
                ],
            )
        )
        assert response.tool_calls[0].arguments == {"content": "喜欢川菜"}
        assert response.usage.prompt_tokens == 10
        await client.aclose()

    asyncio.run(scenario())


def test_openai_provider_parses_stream_deltas():
    body = (
        'data: {"choices":[{"delta":{"content":"你"},"finish_reason":null}]}\n\n'
        'data: {"choices":[{"delta":{"content":"好"},"finish_reason":"stop"}],'
        '"usage":{"prompt_tokens":2,"completion_tokens":2}}\n\n'
        "data: [DONE]\n\n"
    )

    async def handler(_request: httpx.Request):
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    async def scenario():
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        provider = OpenAICompatibleProvider(
            "https://example.test/v1", "secret", "model", client=client
        )
        events = [
            event
            async for event in provider.stream_response(
                LLMRequest(messages=[ModelMessage(role="user", content="hello")])
            )
        ]
        assert [event.text for event in events if event.type == "text_delta"] == ["你", "好"]
        assert events[-1].usage.completion_tokens == 2
        await client.aclose()

    asyncio.run(scenario())


def test_openai_provider_serializes_assistant_tool_calls():
    provider = OpenAICompatibleProvider(
        "https://example.test/v1", "secret", "model", client=httpx.AsyncClient()
    )
    request = LLMRequest(
        messages=[
            ModelMessage(
                role="assistant",
                content="",
                tool_calls=[
                    __import__("app.llm.models", fromlist=["ToolCall"]).ToolCall(
                        id="call-1", name="create_memory", arguments={"content": "川菜"}
                    )
                ],
            )
        ]
    )
    message = provider._payload(request, stream=False)["messages"][0]
    assert message["tool_calls"][0]["function"]["arguments"] == '{"content": "川菜"}'
    asyncio.run(provider._client.aclose())
