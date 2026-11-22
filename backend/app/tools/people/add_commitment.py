from pydantic import BaseModel, Field

from app.tools.base import AgentTool, SideEffect, ToolContext


class AddCommitmentInput(BaseModel):
    person_name: str = Field(description="对谁的承诺")
    content: str = Field(min_length=1, max_length=500, description="承诺内容")


class CommitmentOutput(BaseModel):
    id: str
    person_name: str
    content: str
    status: str


class AddCommitmentTool(AgentTool["AddCommitmentInput", "CommitmentOutput"]):
    name = "add_commitment"
    description = (
        "记录用户对某人的社交承诺。当用户说'我答应了xxx''跟xxx说好了''回头给xxx'"
        "之类的承诺时使用。"
    )
    input_model = AddCommitmentInput
    output_model = CommitmentOutput
    side_effect = SideEffect.WRITE

    async def execute(self, ctx: ToolContext, params: AddCommitmentInput) -> CommitmentOutput:
        person = await ctx.service.people.get_by_name(ctx.user_id, params.person_name)
        if person is None:
            person = await ctx.service.people.add_or_update(
                user_id=ctx.user_id, name=params.person_name, relationship="朋友"
            )
        commitment = await ctx.service.people.add_commitment(
            user_id=ctx.user_id,
            person_id=person.id,
            content=params.content,
            source_message_id=ctx.source_message_id,
        )
        return CommitmentOutput(
            id=commitment.id,
            person_name=params.person_name,
            content=commitment.content,
            status=commitment.status,
        )
