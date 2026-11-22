from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel

from app.application.services import ApplicationService

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class SideEffect(StrEnum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"


class ToolContext(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    user_id: str
    conversation_id: str
    run_id: str
    source_message_id: str
    call_id: str
    timezone: str
    service: ApplicationService
    provider: Any = None
    persona_name: str | None = None


class AgentTool(ABC, Generic[InputT, OutputT]):
    name: ClassVar[str]
    description: ClassVar[str]
    input_model: ClassVar[type[BaseModel]]
    output_model: ClassVar[type[BaseModel]]
    side_effect: ClassVar[SideEffect] = SideEffect.NONE
    timeout_seconds: ClassVar[float] = 15

    @abstractmethod
    async def execute(self, ctx: ToolContext, params: InputT) -> OutputT: ...
