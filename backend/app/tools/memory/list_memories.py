from pydantic import BaseModel

from app.tools.base import AgentTool, SideEffect, ToolContext


class ListMemoriesInput(BaseModel):
    pass


class MemoryItem(BaseModel):
    id: str
    content: str
    type: str
    subject: str


class ListMemoriesOutput(BaseModel):
    memories: list[MemoryItem]


class ListMemoriesTool(AgentTool[ListMemoriesInput, ListMemoriesOutput]):
    name = "list_memories"
    description = "列出当前用户已保存且仍有效的长期记忆。"
    input_model = ListMemoriesInput
    output_model = ListMemoriesOutput
    side_effect = SideEffect.READ

    async def execute(self, ctx: ToolContext, params: ListMemoriesInput) -> ListMemoriesOutput:
        del params
        memories = await ctx.service.list_memories(ctx.user_id)
        return ListMemoriesOutput(
            memories=[
                MemoryItem(
                    id=item.id,
                    content=item.content,
                    type=item.type,
                    subject=item.subject,
                )
                for item in memories
            ]
        )
