from datetime import datetime

from pydantic import BaseModel

from app.tools.base import AgentTool, SideEffect, ToolContext


class ListTasksInput(BaseModel):
    pass


class TaskItem(BaseModel):
    id: str
    title: str
    remind_at: datetime | None
    status: str


class ListTasksOutput(BaseModel):
    tasks: list[TaskItem]


class ListTasksTool(AgentTool[ListTasksInput, ListTasksOutput]):
    name = "list_tasks"
    description = "列出当前用户尚未完成的待办和提醒。"
    input_model = ListTasksInput
    output_model = ListTasksOutput
    side_effect = SideEffect.READ

    async def execute(self, ctx: ToolContext, params: ListTasksInput) -> ListTasksOutput:
        del params
        tasks = await ctx.service.list_tasks(ctx.user_id)
        return ListTasksOutput(
            tasks=[
                TaskItem(
                    id=item.id,
                    title=item.title,
                    remind_at=item.remind_at,
                    status=item.status,
                )
                for item in tasks
            ]
        )
