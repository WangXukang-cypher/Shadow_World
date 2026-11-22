from pydantic import BaseModel

from app.tools.base import AgentTool, SideEffect, ToolContext

from .builtin_skills import BUILTIN_SKILLS


class ListSkillsInput(BaseModel):
    pass


class SkillItem(BaseModel):
    id: str
    name: str
    description: str
    is_builtin: bool


class ListSkillsOutput(BaseModel):
    skills: list[SkillItem]


class ListSkillsTool(AgentTool["ListSkillsInput", "ListSkillsOutput"]):
    name = "list_skills"
    description = "列出所有可用技能（内置 + 用户自定义）。用户想知道有哪些技能时调用。"
    input_model = ListSkillsInput
    output_model = ListSkillsOutput
    side_effect = SideEffect.READ

    async def execute(self, ctx: ToolContext, params: ListSkillsInput) -> ListSkillsOutput:
        items = [
            SkillItem(id=s["id"], name=s["name"], description=s["description"], is_builtin=True)
            for s in BUILTIN_SKILLS
        ]
        user_skills = await ctx.service.skills.list(ctx.user_id)
        for s in user_skills:
            items.append(
                SkillItem(id=s.id, name=s.name, description=s.description, is_builtin=False)
            )
        return ListSkillsOutput(skills=items)
