from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from app.tools.base import AgentTool, SideEffect, ToolContext


class GetTimeInput(BaseModel):
    pass


class GetTimeOutput(BaseModel):
    datetime_iso: str
    date: str
    time: str
    weekday: str
    timezone: str


WEEKDAYS_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class GetCurrentTimeTool(AgentTool["GetTimeInput", "GetTimeOutput"]):
    name = "get_current_time"
    description = "获取当前日期和时间。创建待办或提醒前必须先调用此工具确认日期。"
    input_model = GetTimeInput
    output_model = GetTimeOutput
    side_effect = SideEffect.NONE

    async def execute(self, ctx: ToolContext, params: GetTimeInput) -> GetTimeOutput:
        tz = ZoneInfo(ctx.timezone)
        now = datetime.now(tz)
        return GetTimeOutput(
            datetime_iso=now.isoformat(),
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            weekday=WEEKDAYS_CN[now.weekday()],
            timezone=ctx.timezone,
        )
