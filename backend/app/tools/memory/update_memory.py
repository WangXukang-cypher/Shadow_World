from pydantic import BaseModel, Field

from app.tools.base import AgentTool, SideEffect, ToolContext


class UpdateMemoryInput(BaseModel):
    memory_id: str = Field(description="要修改的记忆ID")
    content: str = Field(min_length=1, max_length=2000, description="新的记忆内容")


class UpdateMemoryOutput(BaseModel):
    id: str
    content: str
    type: str


class UpdateMemoryTool(AgentTool["UpdateMemoryInput", "UpdateMemoryOutput"]):
    name = "update_memory"
    description = "修改一条已有记忆的内容。需要先用 list_memories 获取记忆 ID。"
    input_model = UpdateMemoryInput
    output_model = UpdateMemoryOutput
    side_effect = SideEffect.WRITE

    async def execute(self, ctx: ToolContext, params: UpdateMemoryInput) -> UpdateMemoryOutput:
        memory = await ctx.service.memories.update(ctx.user_id, params.memory_id, params.content)
        return UpdateMemoryOutput(id=memory.id, content=memory.content, type=memory.type)
