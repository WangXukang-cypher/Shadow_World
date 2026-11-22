from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ToolCallRead(BaseModel):
    id: str
    call_id: str
    tool_name: str
    status: str
    side_effect: str
    latency_ms: int | None
    error_code: str | None
    result_preview: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None


class RunDetail(BaseModel):
    id: str
    conversation_id: str
    status: str
    route: str
    model_name: str
    iteration_count: int
    prompt_tokens: int
    completion_tokens: int
    error_code: str | None
    cancel_requested_at: datetime | None
    created_at: datetime
    completed_at: datetime | None
    tool_calls: list[ToolCallRead]


class RunCancelResponse(BaseModel):
    id: str
    status: str
    cancel_requested: bool
