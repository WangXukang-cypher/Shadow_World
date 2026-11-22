from pydantic import BaseModel, Field

from app.tools.base import AgentTool, SideEffect, ToolContext


class AddPersonInput(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="人物姓名")
    relationship: str = Field(default="朋友", description="关系：朋友/同事/家人/同学/恋人/其他")
    nickname: str | None = Field(default=None, description="昵称/外号")
    traits: str | None = Field(default=None, description="性格特点，逗号分隔")
    birthday: str | None = Field(default=None, description="生日，格式 MM-DD 或 YYYY-MM-DD")
    notes: str | None = Field(default=None, description="备注信息")


class PersonOutput(BaseModel):
    id: str
    name: str
    relationship: str
    nickname: str | None = None
    traits: str | None = None
    birthday: str | None = None
    notes: str | None = None
    mention_count: int = 0


class AddPersonTool(AgentTool["AddPersonInput", "PersonOutput"]):
    name = "add_person"
    description = (
        "记录用户提到的人物信息。当用户聊天中提到某个人并透露了关系、性格、"
        "生日等信息时使用。如果人物已存在则更新信息。"
    )
    input_model = AddPersonInput
    output_model = PersonOutput
    side_effect = SideEffect.WRITE

    async def execute(self, ctx: ToolContext, params: AddPersonInput) -> PersonOutput:
        person = await ctx.service.people.add_or_update(
            user_id=ctx.user_id,
            name=params.name,
            relationship=params.relationship,
            nickname=params.nickname,
            traits=params.traits,
            birthday=params.birthday,
            notes=params.notes,
        )
        return PersonOutput(
            id=person.id,
            name=person.name,
            relationship=person.relationship,
            nickname=person.nickname,
            traits=person.traits,
            birthday=person.birthday,
            notes=person.notes,
            mention_count=person.mention_count,
        )
