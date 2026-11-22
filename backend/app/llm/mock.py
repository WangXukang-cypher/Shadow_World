import json
from collections.abc import AsyncIterator

from app.agent.mock_provider import MockLLMProvider as LegacyMockProvider

from .models import (
    LLMEvent,
    LLMRequest,
    LLMResponse,
    MessageRole,
    ResponseCompleted,
    TextDelta,
    ToolCall,
    ToolCallDelta,
)


class MockLLMProvider:
    name = "mock"

    def __init__(self):
        self._legacy = LegacyMockProvider()

    async def create_response(self, request: LLMRequest) -> LLMResponse:
        if request.messages and request.messages[-1].role == MessageRole.TOOL:
            return self._finalize_tool(request.messages[-1].name, request.messages[-1].content)

        user_text = next(
            (
                message.content
                for message in reversed(request.messages)
                if message.role == MessageRole.USER
            ),
            "",
        )
        decision = self._legacy.decide(user_text)
        tool_names = {tool.name for tool in request.tools}
        if decision.route in tool_names:
            arguments: dict[str, str] = {}
            if decision.argument is not None:
                argument_name = "content" if decision.route == "create_memory" else "title"
                arguments[argument_name] = decision.argument
            return LLMResponse(
                tool_calls=[
                    ToolCall(
                        id=f"mock-{decision.route}",
                        name=decision.route,
                        arguments=arguments,
                    )
                ],
                finish_reason="tool_calls",
            )
        return LLMResponse(text=decision.reply, finish_reason="stop")

    @staticmethod
    def _finalize_tool(tool_name: str | None, content: str) -> LLMResponse:
        data = json.loads(content)
        if tool_name == "create_memory":
            return LLMResponse(text=f"好的，我记住了：{data['content']}", finish_reason="stop")
        if tool_name == "list_memories":
            items = data["memories"]
            text = (
                "我还没有保存长期记忆。"
                if not items
                else "我记得：\n" + "\n".join(f"- {item['content']}" for item in items)
            )
            return LLMResponse(text=text, finish_reason="stop")
        if tool_name == "create_task":
            return LLMResponse(text=f"已创建待办：{data['title']}", finish_reason="stop")
        if tool_name == "list_tasks":
            items = data["tasks"]
            text = (
                "当前没有未完成待办。"
                if not items
                else "你的待办：\n" + "\n".join(f"- {item['title']}" for item in items)
            )
            return LLMResponse(text=text, finish_reason="stop")
        return LLMResponse(text="工具调用已完成。", finish_reason="stop")

    async def stream_response(self, request: LLMRequest) -> AsyncIterator[LLMEvent]:
        response = await self.create_response(request)
        for start in range(0, len(response.text), 8):
            yield TextDelta(text=response.text[start : start + 8])
        for index, call in enumerate(response.tool_calls):
            yield ToolCallDelta(
                index=index,
                call_id=call.id,
                name=call.name,
                arguments_delta=json.dumps(call.arguments, ensure_ascii=False),
            )
        yield ResponseCompleted(finish_reason=response.finish_reason, usage=response.usage)
