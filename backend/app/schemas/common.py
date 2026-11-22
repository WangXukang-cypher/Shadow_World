from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SSEEvent(BaseModel):
    id: int
    event: str
    data: dict[str, Any]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    provider: str
    mode: str = "mature-foundation"
    database: str = "ok"
    timestamp: datetime


class PageInfo(BaseModel):
    next_cursor: str | None = None
    has_more: bool = False


class ToolStatus(BaseModel):
    tool: str = Field(min_length=1)
    status: str
