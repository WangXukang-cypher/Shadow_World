import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from app.llm.base import LLMProvider
from app.llm.models import (
    LLMRequest,
    ResponseCompleted,
    TextDelta,
    ToolCall,
    ToolCallDelta,
    Usage,
)


@dataclass
class _PendingToolCall:
    call_id: str = ""
    name: str = ""
    arguments: str = ""


@dataclass
class StreamedModelResult:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    usage: Usage = field(default_factory=Usage)


async def stream_model_response(
    provider: LLMProvider,
    request: LLMRequest,
    on_text: Callable[[str], Awaitable[None]],
) -> StreamedModelResult:
    text_parts: list[str] = []
    pending: dict[int, _PendingToolCall] = {}
    finish_reason: str | None = None
    usage = Usage()
    async for event in provider.stream_response(request):
        if isinstance(event, TextDelta):
            text_parts.append(event.text)
            await on_text(event.text)
        elif isinstance(event, ToolCallDelta):
            item = pending.setdefault(event.index, _PendingToolCall())
            if event.call_id:
                item.call_id = event.call_id
            if event.name:
                item.name = event.name
            item.arguments += event.arguments_delta
        elif isinstance(event, ResponseCompleted):
            finish_reason = event.finish_reason
            usage = event.usage
    tool_calls = []
    for index in sorted(pending):
        item = pending[index]
        tool_calls.append(
            ToolCall(
                id=item.call_id or f"call-{index}",
                name=item.name,
                arguments=json.loads(item.arguments or "{}"),
            )
        )
    return StreamedModelResult(
        text="".join(text_parts),
        tool_calls=tool_calls,
        finish_reason=finish_reason,
        usage=usage,
    )
