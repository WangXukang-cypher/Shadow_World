from typing import Annotated

from fastapi import Depends, Request

from app.agent.runtime import AgentRuntime
from app.application.services import DEFAULT_USER_ID, ApplicationService
from app.notifications.broker import EventBroker


def get_user_id(request: Request) -> str:
    """匿名多用户：从 UserSessionMiddleware 注入的会话状态读取。

    中间件未覆盖的路径（如测试直连）回退到 default 用户。
    """
    user_id = getattr(request.state, "user_id", None)
    return user_id if user_id else DEFAULT_USER_ID


def get_service(request: Request) -> ApplicationService:
    return request.app.state.service


def get_runtime(request: Request) -> AgentRuntime:
    return request.app.state.runtime


def get_broker(request: Request) -> EventBroker:
    return request.app.state.broker


UserIdDep = Annotated[str, Depends(get_user_id)]
ServiceDep = Annotated[ApplicationService, Depends(get_service)]
RuntimeDep = Annotated[AgentRuntime, Depends(get_runtime)]
BrokerDep = Annotated[EventBroker, Depends(get_broker)]
