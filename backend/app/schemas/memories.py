from datetime import datetime

from pydantic import BaseModel, Field

from .common import ORMModel


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    type: str = Field(default="fact", min_length=1, max_length=40)
    subject: str = Field(default="我", min_length=1, max_length=200)


class MemoryRead(ORMModel):
    id: str
    user_id: str
    type: str
    subject: str
    content: str
    normalized_key: str
    status: str
    source_message_id: str | None
    created_at: datetime
    updated_at: datetime
