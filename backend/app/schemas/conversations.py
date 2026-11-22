from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .common import ORMModel


class ConversationCreate(BaseModel):
    title: str = Field(default="", max_length=200)
    is_group: bool = False
    persona_ids: list[dict] | None = None
    max_auto_replies: int = Field(default=2, ge=0, le=10, description="群聊中AI人格自动互动最大轮次")


class ConversationPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)


class ConversationRead(ORMModel):
    id: str
    user_id: str
    title: str
    next_message_seq: int
    is_group: bool = False
    persona_ids: list[dict] | None = None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PersonaInfo(BaseModel):
    name: str = Field(max_length=50)
    style: str = Field(max_length=200)
    traits: str = Field(max_length=200)
    addressUser: str = Field(max_length=30, alias="addressUser")
    model: str | None = None


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    persona: PersonaInfo | None = None
    target_persona: str | None = Field(default=None, description="指定回复的人格名")
    reply_to_id: str | None = Field(default=None, description="引用的消息ID")


class MessageRead(ORMModel):
    id: str
    user_id: str
    conversation_id: str
    role: Literal["user", "assistant", "tool", "system"]
    seq: int
    content: str
    status: str
    persona_name: str | None = None
    persona_avatar: str | None = None
    reply_to_id: str | None = None
    created_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead]


class RunAccepted(BaseModel):
    id: str
    status: str
    conversation_id: str
