from pydantic import BaseModel, Field

from app.tools.base import AgentTool, SideEffect, ToolContext


class CompleteTaskInput(BaseModel):
    task_id: str = Field(description="要完成的待办ID")


class CompleteTaskOutput(BaseModel):
    id: str
    title: str
    status: str


class CompleteTaskTool(AgentTool["CompleteTaskInput", "CompleteTaskOutput"]):
    name = "complete_task"
    description = "将一条待办标记为已完成。需要先用 list_tasks 获取待办 ID。"
    input_model = CompleteTaskInput
    output_model = CompleteTaskOutput
    side_effect = SideEffect.WRITE

    async def execute(self, ctx: ToolContext, params: CompleteTaskInput) -> CompleteTaskOutput:
        task = await ctx.service.tasks.complete(ctx.user_id, params.task_id)
        return CompleteTaskOutput(id=task.id, title=task.title, status=task.status)
