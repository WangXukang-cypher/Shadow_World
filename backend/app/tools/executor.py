import asyncio
import json
import time
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.errors import AppError, ErrorCategory

from .base import ToolContext
from .idempotency import build_idempotency_key
from .registry import ToolRegistry


class ToolExecutionResult(BaseModel):
    tool_name: str
    output: dict[str, Any]
    model_content: str


class ToolExecutor:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def execute(
        self,
        name: str,
        raw_arguments: dict[str, Any],
        context: ToolContext,
        allowed: set[str] | None = None,
    ) -> ToolExecutionResult:
        if allowed is not None and name not in allowed:
            raise AppError(
                "TOOL_NOT_ALLOWED",
                "当前场景不允许调用该工具。",
                400,
                ErrorCategory.VALIDATION,
            )
        try:
            tool = self.registry.get(name)
        except KeyError as exc:
            raise AppError(
                "TOOL_NOT_FOUND",
                "模型选择了不存在的工具。",
                400,
                ErrorCategory.VALIDATION,
            ) from exc
        try:
            params = tool.input_model.model_validate(raw_arguments)
        except ValidationError as exc:
            raise AppError(
                "TOOL_ARGUMENT_INVALID",
                "工具参数不合法。",
                400,
                ErrorCategory.VALIDATION,
                details=exc.errors(include_url=False),
            ) from exc

        arguments = params.model_dump(mode="json")
        idempotency_key = build_idempotency_key(
            context.user_id, context.source_message_id, name, arguments
        )
        existing = await context.service.get_tool_call_by_idempotency_key(idempotency_key)
        if existing is not None:
            if existing.status == "completed" and existing.result is not None:
                return ToolExecutionResult(
                    tool_name=name,
                    output=existing.result,
                    model_content=existing.model_content
                    or json.dumps(existing.result, ensure_ascii=False),
                )
            raise AppError(
                "TOOL_CALL_ALREADY_RECORDED",
                "相同工具操作已在本次请求中执行或处理中。",
                409,
                ErrorCategory.CONFLICT,
            )

        record = await context.service.create_tool_call(
            run_id=context.run_id,
            call_id=context.call_id,
            tool_name=name,
            arguments=arguments,
            side_effect=tool.side_effect.value,
            idempotency_key=idempotency_key,
        )
        started = time.perf_counter()
        try:
            output = await asyncio.wait_for(
                tool.execute(context, params), timeout=tool.timeout_seconds
            )
        except TimeoutError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            await context.service.fail_tool_call(record.id, "TOOL_TIMEOUT", latency_ms)
            raise AppError(
                "TOOL_TIMEOUT",
                "工具执行超时。",
                504,
                ErrorCategory.INTERNAL,
            ) from exc
        except Exception:
            latency_ms = int((time.perf_counter() - started) * 1000)
            await context.service.fail_tool_call(record.id, "TOOL_EXECUTION_FAILED", latency_ms)
            raise
        data = output.model_dump(mode="json")
        model_content = output.model_dump_json()
        latency_ms = int((time.perf_counter() - started) * 1000)
        await context.service.complete_tool_call(record.id, data, model_content, latency_ms)
        return ToolExecutionResult(
            tool_name=name,
            output=data,
            model_content=model_content,
        )
