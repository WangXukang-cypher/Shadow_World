from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ImageUrlContent(BaseModel):
    type: Literal["image_url"] = "image_url"
    image_url: dict[str, str]


ContentPart = TextContent | ImageUrlContent


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class ModelMessage(BaseModel):
    role: MessageRole
    content: str | list[ContentPart]
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)

    @property
    def text_content(self) -> str:
        if isinstance(self.content, str):
            return self.content
        parts = [p.text for p in self.content if isinstance(p, TextContent)]
        return "\n".join(parts)


class LLMRequest(BaseModel):
    messages: list[ModelMessage]
    tools: list[ToolDefinition] = Field(default_factory=list)
    temperature: float = 0.2
    max_tokens: int = 2048


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMResponse(BaseModel):
    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: str | None = None
    usage: Usage = Field(default_factory=Usage)


class TextDelta(BaseModel):
    type: Literal["text_delta"] = "text_delta"
    text: str


class ToolCallDelta(BaseModel):
    type: Literal["tool_call_delta"] = "tool_call_delta"
    index: int
    call_id: str | None = None
    name: str | None = None
    arguments_delta: str = ""


class ResponseCompleted(BaseModel):
    type: Literal["completed"] = "completed"
    finish_reason: str | None = None
    usage: Usage = Field(default_factory=Usage)


LLMEvent = TextDelta | ToolCallDelta | ResponseCompleted
