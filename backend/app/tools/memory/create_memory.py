from pydantic import BaseModel, Field

from app.tools.base import AgentTool, SideEffect, ToolContext


class CreateMemoryInput(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    type: str = Field(default="fact", max_length=40)
    subject: str = Field(default="我", max_length=200)


class CreateMemoryOutput(BaseModel):
    id: str
    content: str
    type: str
    subject: str


class CreateMemoryTool(AgentTool[CreateMemoryInput, CreateMemoryOutput]):
    name = "create_memory"
    description = "保存用户明确要求长期记住的事实、偏好或约束。"
    input_model = CreateMemoryInput
    output_model = CreateMemoryOutput
    side_effect = SideEffect.WRITE

    async def execute(self, ctx: ToolContext, params: CreateMemoryInput) -> CreateMemoryOutput:
        tags = f"persona:{ctx.persona_name}" if ctx.persona_name else None
        memory = await ctx.service.create_memory(
            ctx.user_id,
            params.content,
            params.type,
            params.subject,
            ctx.source_message_id,
            tags=tags,
        )
        return CreateMemoryOutput(
            id=memory.id,
            content=memory.content,
            type=memory.type,
            subject=memory.subject,
        )
