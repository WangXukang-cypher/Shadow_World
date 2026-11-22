import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.agent.runtime import AgentRuntime
from app.application.rate_limit import RunLimiter
from app.application.services import ApplicationService
from app.core.config import Settings
from app.infrastructure.db.session import create_engine, create_session_factory
from app.llm.base import LLMProvider
from app.llm.failover import FailoverProvider
from app.llm.mock import MockLLMProvider
from app.llm.openai_compatible import OpenAICompatibleProvider
from app.notifications.broker import EventBroker
from app.notifications.reminder_worker import ReminderWorker
from app.tools import ToolExecutor, ToolRegistry, build_tooling

logger = logging.getLogger(__name__)


def build_llm_providers(settings: Settings) -> tuple[LLMProvider, LLMProvider | None]:
    """根据配置构建 (主 provider, 群聊 provider)。

    openai-compatible 配置不完整时降级为 mock，保证服务可启动，
    用户在设置页补齐 API Key 后热更新即可切换。
    """
    if settings.llm_provider == "mock":
        return MockLLMProvider(), None
    if settings.llm_provider != "openai-compatible":
        raise ValueError(f"unsupported LLM_PROVIDER: {settings.llm_provider}")

    if not settings.llm_base_url or not settings.llm_api_key or not settings.llm_model:
        logger.warning(
            "LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 未配置完整，暂用 mock provider。"
            "请在前端设置页选择服务商并填写 API Key。"
        )
        return MockLLMProvider(), None

    primary = OpenAICompatibleProvider(
        settings.llm_base_url,
        settings.llm_api_key,
        settings.llm_model,
        settings.llm_timeout_seconds,
    )
    provider: LLMProvider = FailoverProvider(primary, fallback=MockLLMProvider(), max_retries=2)

    group_provider: LLMProvider | None = None
    group_base = getattr(settings, "group_llm_base_url", "") or ""
    group_key = getattr(settings, "group_llm_api_key", "") or ""
    group_model = getattr(settings, "group_llm_model", "") or ""
    if group_base and group_key and group_model:
        group_provider = OpenAICompatibleProvider(group_base, group_key, group_model, 30)
    return provider, group_provider


@dataclass
class Container:
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]
    service: ApplicationService
    broker: EventBroker
    limiter: RunLimiter
    runtime: AgentRuntime
    provider: LLMProvider
    tool_registry: ToolRegistry
    tool_executor: ToolExecutor
    reminder_worker: ReminderWorker


def build_container(settings: Settings) -> Container:
    engine = create_engine(settings)
    sessions = create_session_factory(engine)
    service = ApplicationService(sessions)
    broker = EventBroker()
    limiter = RunLimiter(
        settings.max_active_runs_per_user,
        settings.max_global_runs,
        settings.message_rate_limit_per_minute,
    )
    tool_registry, tool_executor = build_tooling()
    provider, group_provider = build_llm_providers(settings)
    runtime = AgentRuntime(
        service,
        provider,
        limiter,
        broker,
        tool_registry,
        tool_executor,
        settings.timezone,
        llm_timeout=settings.llm_timeout_seconds,
    )
    # 群聊自动回复用独立 Provider（如果配置了 group provider）
    runtime.group_provider = group_provider
    reminder_worker = ReminderWorker(service, broker, settings.reminder_poll_seconds)
    return Container(
        engine=engine,
        sessions=sessions,
        service=service,
        broker=broker,
        limiter=limiter,
        runtime=runtime,
        provider=provider,
        tool_registry=tool_registry,
        tool_executor=tool_executor,
        reminder_worker=reminder_worker,
    )
