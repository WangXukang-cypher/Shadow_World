import asyncio
import json
import logging
from typing import Any

from app.agent.context import ContextBuilder
from app.agent.streaming import stream_model_response
from app.application.rate_limit import RunLimiter
from app.application.services import DEFAULT_USER_ID, ApplicationService
from app.llm.base import LLMProvider
from app.llm.models import LLMRequest, ModelMessage, ToolCall, Usage
from app.notifications.broker import EventBroker
from app.tools import ToolContext, ToolExecutor, ToolRegistry

logger = logging.getLogger(__name__)
ALLOWED_TOOLS = {
    "get_current_time",
    "create_memory", "list_memories", "update_memory", "delete_memory",
    "create_task", "list_tasks", "complete_task", "delete_task",
    "add_person", "list_people", "add_commitment",
    "list_skills", "manage_skill", "invoke_skill",
    "web_search",
}


class RunCancelled(Exception):
    pass


class RepeatedToolCall(Exception):
    pass


class AgentRuntime:
    def __init__(
        self,
        service: ApplicationService,
        provider: LLMProvider,
        limiter: RunLimiter,
        broker: EventBroker,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        timezone_name: str,
        llm_timeout: float = 60.0,
    ):
        self.service = service
        self.provider = provider
        self.limiter = limiter
        self.broker = broker
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.timezone_name = timezone_name
        self.llm_timeout = llm_timeout
        self.context_builder = ContextBuilder(service)
        self._tasks: dict[str, asyncio.Task] = {}
        self.group_provider = None  # set by bootstrap
        # 用户私有 provider 缓存（每个用户自己的 API Key，互不共享）
        self._user_providers: dict[str, Any] = {}
        self._user_provider_limit = 512

    def _get_provider_for_model(self, provider: Any, model: str | None):
        """根据 model 字段选择 provider（provider 为该用户的 provider）。"""
        if not model or model == "default" or model == "kimi":
            from app.llm.failover import FailoverProvider as FP
            return provider.primary if isinstance(provider, FP) else provider
        if model in ("qwen", "group"):
            return self.group_provider or provider
        return provider

    async def resolve_user_provider(self, user_id: str) -> Any:
        """用户自配模型优先（自己的 Key），未配置回退全局 provider。"""
        cached = self._user_providers.get(user_id)
        if cached is not None:
            return cached
        setting = await self.service.get_user_llm_setting(user_id)
        if setting is not None and setting.api_key and setting.base_url and setting.model:
            from app.llm.openai_compatible import OpenAICompatibleProvider

            provider = OpenAICompatibleProvider(
                setting.base_url, setting.api_key, setting.model, self.llm_timeout
            )
            provider.name = setting.model
            if len(self._user_providers) >= self._user_provider_limit:
                self._evict_oldest_user_provider()
            self._user_providers[user_id] = provider
            return provider
        return self.provider

    def _evict_oldest_user_provider(self) -> None:
        oldest_user_id = next(iter(self._user_providers))
        provider = self._user_providers.pop(oldest_user_id, None)
        close = getattr(provider, "close", None)
        if close is not None:
            try:
                asyncio.get_running_loop().create_task(close())
            except RuntimeError:
                pass

    async def invalidate_user_provider(self, user_id: str) -> None:
        """用户更新配置后调用：关闭并移除缓存的 provider，下次请求重建。"""
        provider = self._user_providers.pop(user_id, None)
        if provider is not None:
            close = getattr(provider, "close", None)
            if close is not None:
                try:
                    await close()
                except Exception:  # noqa: BLE001 - 关闭旧 provider 的失败不影响配置更新
                    logger.warning("failed to close user provider for %s", user_id)

    async def start(
        self, conversation_id: str, text: str, user_id: str = DEFAULT_USER_ID,
        persona: dict | None = None, target_persona: str | None = None, reply_to_id: str | None = None
    ) -> dict[str, Any]:
        await self.limiter.reserve(user_id)
        try:
            user_message = await self.service.add_message(user_id, conversation_id, "user", text)
            run = await self.service.create_run(user_id, conversation_id, user_message.id)
            task = asyncio.create_task(
                self._execute(run.id, conversation_id, user_message.id, user_id, persona, target_persona)
            )
            self._tasks[run.id] = task
            task.add_done_callback(lambda _task, run_id=run.id: self._tasks.pop(run_id, None))
            return {"id": run.id, "status": run.status, "conversation_id": conversation_id}
        except Exception:
            await self.limiter.release(user_id, global_acquired=False)
            raise

    async def cancel(self, run_id: str, user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
        run = await self.service.request_run_cancel(user_id, run_id)
        task = self._tasks.get(run_id)
        if run.status == "running" and task is not None and not task.done():
            task.cancel()
        return {"id": run.id, "status": run.status, "cancel_requested": True}

    def is_run_active(self, run_id: str) -> bool:
        """run 是否仍在当前进程中执行（用于识别后端重启产生的僵尸 run）。"""
        task = self._tasks.get(run_id)
        return task is not None and not task.done()

    async def _emit(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        event = await self.service.append_run_event(run_id, event_type, payload)
        await self.broker.publish_run(
            run_id,
            {"id": event.seq, "event": event.event_type, "data": event.payload},
        )

    async def _check_cancelled(self, run_id: str) -> None:
        if await self.service.is_run_cancel_requested(run_id):
            raise RunCancelled

    async def _execute(
        self,
        run_id: str,
        conversation_id: str,
        source_message_id: str,
        user_id: str,
        persona: dict | None = None,
        target_persona: str | None = None,
    ) -> None:
        route = "chat"
        global_acquired = False
        iteration_count = 0
        total_usage = Usage()
        seen_tool_calls: set[str] = set()
        try:
            await self.limiter.acquire_global()
            global_acquired = True
            provider = await self.resolve_user_provider(user_id)
            await self.service.set_run_status(
                run_id, "running", route, model_name=provider.name
            )
            await self._emit(run_id, "run.started", {"run_id": run_id})
            # 群聊时注入群成员信息到 persona
            if persona:
                try:
                    conv = await self.service.get_conversation(user_id, conversation_id)
                    if getattr(conv, "is_group", False) and conv.persona_ids:
                        members = "、".join(p.get("name", "") for p in conv.persona_ids)
                        persona["_group_members"] = members
                except Exception:
                    logger.debug("failed to enrich group context", exc_info=True)
            messages = await self.context_builder.build(user_id, conversation_id, persona=persona)
            reply = ""
            for iteration in range(6):
                iteration_count = iteration + 1
                await self._check_cancelled(run_id)
                emitted_text: list[str] = []

                async def on_text(delta: str, sink: list[str] = emitted_text) -> None:
                    sink.append(delta)
                    await self._emit(run_id, "assistant.delta", {"text": delta})

                active_provider = self._get_provider_for_model(
                    provider, persona.get("model") if persona else None
                )
                response = await stream_model_response(
                    active_provider,
                    LLMRequest(
                        messages=messages,
                        tools=self.tool_registry.definitions(ALLOWED_TOOLS),
                    ),
                    on_text,
                )
                total_usage.prompt_tokens += response.usage.prompt_tokens
                total_usage.completion_tokens += response.usage.completion_tokens
                if not response.tool_calls:
                    reply = response.text
                    break
                if emitted_text:
                    await self._emit(
                        run_id,
                        "assistant.rewind",
                        {"characters": len(response.text)},
                    )
                await self._emit(
                    run_id,
                    "agent.status",
                    {
                        "route": "tool_loop",
                        "iteration": iteration_count,
                        "tool_count": len(response.tool_calls),
                    },
                )
                messages.append(
                    ModelMessage(
                        role="assistant",
                        content=response.text,
                        tool_calls=response.tool_calls,
                    )
                )
                for call in response.tool_calls:
                    signature = self._tool_signature(call)
                    if signature in seen_tool_calls:
                        raise RepeatedToolCall(call.name)
                    seen_tool_calls.add(signature)
                    route = call.name
                    await self._check_cancelled(run_id)
                    await self._execute_tool(
                        run_id,
                        conversation_id,
                        source_message_id,
                        user_id,
                        call,
                        messages,
                        persona_name=persona.get("name") if persona else None,
                        provider=provider,
                    )
            else:
                reply = "工具调用轮次已达上限，请缩小任务范围后重试。"
                await self._emit(run_id, "assistant.delta", {"text": reply})

            await self._check_cancelled(run_id)
            persona_name = persona.get("name") if persona else None
            output_message = await self.service.add_message(
                user_id, conversation_id, "assistant", reply,
                persona_name=persona_name,
            )
            await self.service.set_run_status(
                run_id,
                "completed",
                route,
                output_message_id=output_message.id,
                model_name=provider.name,
                iteration_count=iteration_count,
                prompt_tokens=total_usage.prompt_tokens,
                completion_tokens=total_usage.completion_tokens,
            )
            await self._emit(
                run_id,
                "run.completed",
                {
                    "message": {
                        "id": output_message.id,
                        "user_id": output_message.user_id,
                        "conversation_id": output_message.conversation_id,
                        "role": output_message.role,
                        "seq": output_message.seq,
                        "content": output_message.content,
                        "status": output_message.status,
                        "persona_name": output_message.persona_name,
                        "created_at": output_message.created_at.isoformat(),
                    },
                    "route": route,
                    "usage": total_usage.model_dump(),
                },
            )
            # 群聊自动回复：让其他人格也参与对话
            await self._group_auto_reply(
                run_id, conversation_id, user_id, persona, reply
            )
        except (RunCancelled, asyncio.CancelledError):
            await asyncio.shield(
                self.service.set_run_status(
                    run_id,
                    "cancelled",
                    route,
                    model_name=provider.name,
                    iteration_count=iteration_count,
                    prompt_tokens=total_usage.prompt_tokens,
                    completion_tokens=total_usage.completion_tokens,
                )
            )
            await asyncio.shield(
                self._emit(
                    run_id,
                    "run.cancelled",
                    {"code": "RUN_CANCELLED", "message": "已停止生成。"},
                )
            )
        except RepeatedToolCall as exc:
            await self.service.set_run_status(
                run_id,
                "failed",
                route,
                error_code="REPEATED_TOOL_CALL",
                model_name=provider.name,
                iteration_count=iteration_count,
            )
            await self._emit(
                run_id,
                "run.failed",
                {"code": "REPEATED_TOOL_CALL", "message": f"检测到重复工具调用：{exc}"},
            )
        except Exception as exc:
            logger.exception(
                "agent run failed: run_id=%s route=%s error=%s",
                run_id,
                route,
                type(exc).__name__,
            )
            await self.service.set_run_status(
                run_id,
                "failed",
                route,
                error_code="RUN_FAILED",
                model_name=provider.name,
                iteration_count=iteration_count,
            )
            await self._emit(
                run_id,
                "run.failed",
                {"code": "RUN_FAILED", "message": "处理失败，请稍后重试。"},
            )
        finally:
            await self.limiter.release(user_id, global_acquired)

    async def _execute_tool(
        self,
        run_id: str,
        conversation_id: str,
        source_message_id: str,
        user_id: str,
        call: ToolCall,
        messages: list[ModelMessage],
        persona_name: str | None = None,
        provider: Any = None,
    ) -> None:
        await self._emit(run_id, "tool.started", {"tool": call.name, "call_id": call.id})
        result = await self.tool_executor.execute(
            call.name,
            call.arguments,
            ToolContext(
                user_id=user_id,
                conversation_id=conversation_id,
                run_id=run_id,
                source_message_id=source_message_id,
                call_id=call.id,
                timezone=self.timezone_name,
                service=self.service,
                provider=provider or self.provider,
                persona_name=persona_name,
            ),
            allowed=ALLOWED_TOOLS,
        )
        await self._emit(
            run_id,
            "tool.finished",
            {"tool": call.name, "call_id": call.id, "result": result.output},
        )
        if call.name == "create_memory":
            await self._emit(run_id, "memory.saved", result.output)
        messages.append(
            ModelMessage(
                role="tool",
                name=call.name,
                tool_call_id=call.id,
                content=result.model_content,
            )
        )

    @staticmethod
    def _tool_signature(call: ToolCall) -> str:
        return f"{call.name}:{json.dumps(call.arguments, ensure_ascii=False, sort_keys=True)}"

    async def _group_auto_reply(
        self,
        run_id: str,
        conversation_id: str,
        user_id: str,
        current_persona: dict | None,
        last_reply: str,
    ) -> None:
        """群聊 @链：解析回复中的 @mentions，被@的人格依次回复，支持多@。"""
        import re

        try:
            conv = await self.service.get_conversation(user_id, conversation_id)
        except Exception:  # noqa: BLE001 - missing conversations simply stop the chain
            return
        if not getattr(conv, "is_group", False) or not conv.persona_ids:
            return

        max_global = 100
        persona_map = {p.get("name"): p for p in conv.persona_ids}
        auto_counts: dict[str, int] = {}
        notified_limit: set[str] = set()
        current_name = current_persona.get("name") if current_persona else "用户"
        current_reply = last_reply

        for round_idx in range(max_global):
            mentions = re.findall(r"@(\S+)", current_reply)
            targets = []
            for m in mentions:
                if m in persona_map and m != current_name:
                    p_max = persona_map[m].get("max_replies", 5)
                    if auto_counts.get(m, 0) < p_max:
                        targets.append(m)
                    elif m not in notified_limit:
                        notified_limit.add(m)
                        await self.service.add_message(
                            user_id, conversation_id, "system",
                            f"💤 {m} 的自动回复轮次已达上限（{p_max}轮），下线休息了～",
                            persona_name="system",
                        )
                        await self._emit(run_id, "group.limit_reached", {"persona": m, "limit": p_max})
            if not targets:
                break

            for target in targets:
                auto_counts[target] = auto_counts.get(target, 0) + 1
                await asyncio.sleep(3)

                p = persona_map[target]
                name = p.get("name", "")
                style = p.get("style", "")
                traits = p.get("traits", "")
                address = p.get("addressUser", "你")
                members = "、".join(persona_map.keys())

                system = (
                    f'你是群聊中的"{name}"。群成员有：{members}，还有用户。\n'
                    f'你的风格：{style}。性格：{traits}。称呼用户为：{address}。\n'
                    f'刚才"{current_name}"说（并@了你）：{current_reply[:400]}\n\n'
                    f'请简短回应1-3句话。如果想让其他人参与可以@他们。不需要强行@。直接说话。'
                )

                try:
                    from app.llm.models import LLMRequest, MessageRole
                    from app.llm.models import ModelMessage as MM
                    persona_model = p.get("model")
                    user_provider = await self.resolve_user_provider(user_id)
                    provider = self._get_provider_for_model(user_provider, persona_model or "qwen")
                    request = LLMRequest(
                        messages=[
                            MM(role=MessageRole.SYSTEM, content=system),
                            MM(role=MessageRole.USER, content=f"{name}，有人@你了"),
                        ],
                        tools=[],
                        max_tokens=512,
                        temperature=0.7,
                    )
                    response = await provider.create_response(request)
                    reply_text = response.text.strip()
                    if not reply_text:
                        continue

                    msg = await self.service.add_message(
                        user_id, conversation_id, "assistant", reply_text,
                        persona_name=name,
                    )
                    await self._emit(run_id, "group.auto_reply", {
                        "message": {
                            "id": msg.id,
                            "role": "assistant",
                            "seq": msg.seq,
                            "content": msg.content,
                            "persona_name": name,
                            "created_at": msg.created_at.isoformat(),
                        },
                    })
                    current_reply = reply_text
                    current_name = name
                except Exception as exc:  # noqa: BLE001 - provider failures end the chain safely
                    logger.error("Group @-chain failed for %s: %s", target, exc)
                    return
