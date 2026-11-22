from pydantic import BaseModel, Field

from app.tools.base import AgentTool, SideEffect, ToolContext


class DeleteMemoryInput(BaseModel):
    memory_id: str = Field(description="要删除的记忆ID")


class DeleteMemoryOutput(BaseModel):
    success: bool
    message: str


class DeleteMemoryTool(AgentTool["DeleteMemoryInput", "DeleteMemoryOutput"]):
    name = "delete_memory"
    description = "删除一条记忆。用户明确要求忘记某个信息时使用。需要先用 list_memories 获取记忆 ID。"
    input_model = DeleteMemoryInput
    output_model = DeleteMemoryOutput
    side_effect = SideEffect.DESTRUCTIVE

    async def execute(self, ctx: ToolContext, params: DeleteMemoryInput) -> DeleteMemoryOutput:
        await ctx.service.memories.delete(ctx.user_id, params.memory_id)
        return DeleteMemoryOutput(success=True, message="记忆已删除。")
