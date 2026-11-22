from pydantic import BaseModel, Field

from app.tools.base import AgentTool, SideEffect, ToolContext


class DeleteTaskInput(BaseModel):
    task_id: str = Field(description="要删除的待办ID")


class DeleteTaskOutput(BaseModel):
    success: bool
    message: str


class DeleteTaskTool(AgentTool["DeleteTaskInput", "DeleteTaskOutput"]):
    name = "delete_task"
    description = "删除一条待办。需要先用 list_tasks 获取待办 ID。"
    input_model = DeleteTaskInput
    output_model = DeleteTaskOutput
    side_effect = SideEffect.DESTRUCTIVE

    async def execute(self, ctx: ToolContext, params: DeleteTaskInput) -> DeleteTaskOutput:
        await ctx.service.tasks.delete(ctx.user_id, params.task_id)
        return DeleteTaskOutput(success=True, message="待办已删除。")
