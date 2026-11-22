import json
from collections.abc import AsyncIterator

import httpx

from .models import (
    LLMEvent,
    LLMRequest,
    LLMResponse,
    ModelMessage,
    ResponseCompleted,
    TextDelta,
    ToolCall,
    ToolCallDelta,
    Usage,
)


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60,
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = client is None

    def _payload(self, request: LLMRequest, stream: bool) -> dict:
        messages = [self._message(message) for message in request.messages]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in request.tools
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if stream:
            payload["stream_options"] = {"include_usage": True}
        return payload

    @staticmethod
    def _message(message: ModelMessage) -> dict:
        if isinstance(message.content, list):
            content = [
                part.model_dump() for part in message.content
            ]
        else:
            content = message.content
        result = {"role": message.role.value, "content": content}
        if message.name:
            result["name"] = message.name
        if message.tool_call_id:
            result["tool_call_id"] = message.tool_call_id
        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments, ensure_ascii=False),
                    },
                }
                for call in message.tool_calls
            ]
        return result

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def create_response(self, request: LLMRequest) -> LLMResponse:
        response = await self._client.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers,
            json=self._payload(request, stream=False),
        )
        response.raise_for_status()
        body = response.json()
        choice = body["choices"][0]
        message = choice["message"]
        tool_calls = [
            ToolCall(
                id=item["id"],
                name=item["function"]["name"],
                arguments=json.loads(item["function"].get("arguments") or "{}"),
            )
            for item in (message.get("tool_calls") or [])
        ]
        usage = body.get("usage") or {}
        return LLMResponse(
            text=message.get("content") or message.get("reasoning_content") or "",
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason"),
            usage=Usage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            ),
        )

    async def stream_response(self, request: LLMRequest) -> AsyncIterator[LLMEvent]:
        usage = Usage()
        finish_reason: str | None = None
        async with self._client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=self._headers,
            json=self._payload(request, stream=True),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line.removeprefix("data:").strip()
                if data == "[DONE]":
                    break
                body = json.loads(data)
                raw_usage = body.get("usage")
                if raw_usage:
                    usage = Usage(
                        prompt_tokens=raw_usage.get("prompt_tokens", 0),
                        completion_tokens=raw_usage.get("completion_tokens", 0),
                    )
                for choice in body.get("choices", []):
                    finish_reason = choice.get("finish_reason") or finish_reason
                    delta = choice.get("delta") or {}
                    if delta.get("content"):
                        yield TextDelta(text=delta["content"])
                    for item in (delta.get("tool_calls") or []):
                        function = item.get("function") or {}
                        yield ToolCallDelta(
                            index=item["index"],
                            call_id=item.get("id"),
                            name=function.get("name"),
                            arguments_delta=function.get("arguments") or "",
                        )
        yield ResponseCompleted(finish_reason=finish_reason, usage=usage)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
