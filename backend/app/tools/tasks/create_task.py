from datetime import datetime

from pydantic import BaseModel, Field

from app.agent.time_parser import parse_mock_reminder
from app.tools.base import AgentTool, SideEffect, ToolContext


class CreateTaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    remind_at: datetime | None = None


class CreateTaskOutput(BaseModel):
    id: str
    title: str
    remind_at: datetime | None


class CreateTaskTool(AgentTool[CreateTaskInput, CreateTaskOutput]):
    name = "create_task"
    description = "创建一条待办或带具体时间的提醒。时间不明确时不要调用。"
    input_model = CreateTaskInput
    output_model = CreateTaskOutput
    side_effect = SideEffect.WRITE

    async def execute(self, ctx: ToolContext, params: CreateTaskInput) -> CreateTaskOutput:
        remind_at = params.remind_at or parse_mock_reminder(params.title, ctx.timezone)
        task = await ctx.service.create_task(
            ctx.user_id,
            params.title,
            remind_at=remind_at,
            source_message_id=ctx.source_message_id,
        )
        return CreateTaskOutput(id=task.id, title=task.title, remind_at=task.remind_at)
