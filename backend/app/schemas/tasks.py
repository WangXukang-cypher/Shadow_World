from datetime import datetime

from pydantic import BaseModel, Field

from .common import ORMModel


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    remind_at: datetime | None = None
    due_at: datetime | None = None


class TaskRead(ORMModel):
    id: str
    user_id: str
    title: str
    status: str
    due_at: datetime | None
    remind_at: datetime | None
    notified_at: datetime | None
    source_message_id: str | None
    created_at: datetime
    updated_at: datetime
