from pydantic import BaseModel

from app.tools.base import AgentTool, SideEffect, ToolContext


class ListPeopleInput(BaseModel):
    pass


class PersonItem(BaseModel):
    id: str
    name: str
    relationship: str
    nickname: str | None = None
    traits: str | None = None
    birthday: str | None = None
    notes: str | None = None
    mention_count: int = 0


class ListPeopleOutput(BaseModel):
    people: list[PersonItem]


class ListPeopleTool(AgentTool["ListPeopleInput", "ListPeopleOutput"]):
    name = "list_people"
    description = "列出用户圈子里的所有人物。用户问'我认识谁'或查找某人信息时使用。"
    input_model = ListPeopleInput
    output_model = ListPeopleOutput
    side_effect = SideEffect.READ

    async def execute(self, ctx: ToolContext, params: ListPeopleInput) -> ListPeopleOutput:
        people = await ctx.service.people.list(ctx.user_id)
        items = [
            PersonItem(
                id=p.id,
                name=p.name,
                relationship=p.relationship,
                nickname=p.nickname,
                traits=p.traits,
                birthday=p.birthday,
                notes=p.notes,
                mention_count=p.mention_count,
            )
            for p in people
        ]
        return ListPeopleOutput(people=items)
