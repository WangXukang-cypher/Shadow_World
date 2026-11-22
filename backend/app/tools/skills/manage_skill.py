from typing import Literal

from pydantic import BaseModel, Field

from app.tools.base import AgentTool, SideEffect, ToolContext


class ManageSkillInput(BaseModel):
    action: Literal["create", "update", "delete"] = Field(description="操作类型")
    skill_id: str | None = Field(default=None, description="技能ID，update/delete时必填")
    name: str | None = Field(default=None, max_length=100, description="技能名称，create时必填")
    description: str | None = Field(
        default=None, max_length=500, description="技能描述，create时必填"
    )
    system_prompt: str | None = Field(
        default=None, max_length=4000, description="技能的系统提示词，create时必填"
    )
    source: str | None = Field(
        default="user", description="技能来源：user（用户创建）或 evolved（自进化）"
    )
    trigger_pattern: str | None = Field(
        default=None, max_length=200, description="触发模式描述，如'当用户要翻译+润色时'"
    )


class ManageSkillOutput(BaseModel):
    success: bool
    skill_id: str | None = None
    message: str


class ManageSkillTool(AgentTool["ManageSkillInput", "ManageSkillOutput"]):
    name = "manage_skill"
    description = "创建、更新或删除用户自定义技能。不能修改内置技能。"
    input_model = ManageSkillInput
    output_model = ManageSkillOutput
    side_effect = SideEffect.WRITE

    async def execute(self, ctx: ToolContext, params: ManageSkillInput) -> ManageSkillOutput:
        if params.action == "create":
            if not params.name or not params.description or not params.system_prompt:
                return ManageSkillOutput(
                    success=False, message="创建技能需要提供 name、description 和 system_prompt。"
                )
            skill = await ctx.service.skills.create(
                user_id=ctx.user_id,
                name=params.name,
                description=params.description,
                system_prompt=params.system_prompt,
            )
            return ManageSkillOutput(
                success=True, skill_id=skill.id, message=f"技能「{skill.name}」创建成功。"
            )

        if params.action == "update":
            if not params.skill_id:
                return ManageSkillOutput(success=False, message="更新技能需要提供 skill_id。")
            if params.skill_id.startswith("builtin:"):
                return ManageSkillOutput(success=False, message="不能修改内置技能。")
            skill = await ctx.service.skills.update(
                user_id=ctx.user_id,
                skill_id=params.skill_id,
                name=params.name,
                description=params.description,
                system_prompt=params.system_prompt,
            )
            return ManageSkillOutput(
                success=True, skill_id=skill.id, message=f"技能「{skill.name}」已更新。"
            )

        if params.action == "delete":
            if not params.skill_id:
                return ManageSkillOutput(success=False, message="删除技能需要提供 skill_id。")
            if params.skill_id.startswith("builtin:"):
                return ManageSkillOutput(success=False, message="不能删除内置技能。")
            await ctx.service.skills.delete(user_id=ctx.user_id, skill_id=params.skill_id)
            return ManageSkillOutput(success=True, message="技能已删除。")

        return ManageSkillOutput(success=False, message="未知操作。")
