from pydantic import BaseModel, Field

from app.llm.models import LLMRequest, MessageRole, ModelMessage
from app.tools.base import AgentTool, SideEffect, ToolContext

from .builtin_skills import get_builtin_skill


class InvokeSkillInput(BaseModel):
    skill_id: str = Field(description="技能ID（builtin:xxx 或用户自定义的UUID）")
    input_text: str = Field(min_length=1, max_length=8000, description="需要处理的文本内容")


class InvokeSkillOutput(BaseModel):
    result: str
    skill_name: str


class InvokeSkillTool(AgentTool["InvokeSkillInput", "InvokeSkillOutput"]):
    name = "invoke_skill"
    description = (
        "调用指定技能处理用户输入。技能会使用专门的提示词执行翻译、润色、总结等专项任务。"
        "先用 list_skills 查看可用技能和对应ID。"
    )
    input_model = InvokeSkillInput
    output_model = InvokeSkillOutput
    side_effect = SideEffect.READ
    timeout_seconds = 30

    async def execute(self, ctx: ToolContext, params: InvokeSkillInput) -> InvokeSkillOutput:
        builtin = get_builtin_skill(params.skill_id)
        if builtin:
            skill_name = builtin["name"]
            system_prompt = builtin["system_prompt"]
        else:
            skill = await ctx.service.skills.get(ctx.user_id, params.skill_id)
            skill_name = skill.name
            system_prompt = skill.system_prompt

        if ctx.provider is None:
            return InvokeSkillOutput(
                result="技能执行失败：LLM Provider 未配置。", skill_name=skill_name
            )

        request = LLMRequest(
            messages=[
                ModelMessage(role=MessageRole.SYSTEM, content=system_prompt),
                ModelMessage(role=MessageRole.USER, content=params.input_text),
            ],
            tools=[],
            max_tokens=2048,
        )
        response = await ctx.provider.create_response(request)
        return InvokeSkillOutput(result=response.text, skill_name=skill_name)
