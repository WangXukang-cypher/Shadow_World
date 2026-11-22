from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

from app.api.dependencies import RuntimeDep, ServiceDep, UserIdDep
from app.core.errors import AppError, ErrorCategory
from app.schemas.common import HealthResponse

router = APIRouter(tags=["system"])

# 预设模型服务：用户只需选择服务商并填写 API Key，
# Base URL 和模型名由预设自动填充。每个用户的 Key 相互独立。
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "modelscope": {
        "label": "ModelScope",
        "description": "Qwen",
        "base_url": "https://api-inference.modelscope.cn/v1",
        "model": "Qwen/Qwen3.8-27B",
    },
}


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    async with request.app.state.sessions() as session:
        await session.execute(text("SELECT 1"))
    settings = request.app.state.settings
    return HealthResponse(
        provider=settings.llm_provider,
        timestamp=datetime.now(UTC),
    )


class MeUpdate(BaseModel):
    display_name: str = ""


@router.get("/me")
async def get_me(service: ServiceDep, user_id: UserIdDep):
    user = await service.users.get(user_id)
    display_name = (user.display_name or "") if user else ""
    return {
        "user_id": user_id,
        "display_name": display_name,
        "onboarded": bool(display_name),
    }


@router.patch("/me")
async def update_me(body: MeUpdate, service: ServiceDep, user_id: UserIdDep):
    display_name = body.display_name.strip()
    if not display_name:
        raise AppError("NAME_REQUIRED", "昵称不能为空。", 422, ErrorCategory.VALIDATION)
    user = await service.users.update_display_name(user_id, display_name[:30])
    return {
        "user_id": user.id,
        "display_name": user.display_name,
        "onboarded": True,
    }


class ProviderSettings(BaseModel):
    """用户自己的模型服务配置。

    llm_provider 接受预设名 modelscope 或 openai-compatible；
    预设名自动解析 base_url 和 model；llm_api_key 为空表示沿用现有 Key。
    """

    llm_provider: str = "openai-compatible"
    llm_api_key: str = ""
    llm_base_url: str | None = None
    llm_model: str | None = None


@router.get("/settings/provider")
async def get_provider_settings(request: Request, service: ServiceDep, user_id: UserIdDep):
    setting = await service.get_user_llm_setting(user_id)
    global_settings = request.app.state.settings
    return {
        "llm_provider": setting.provider if setting else "",
        "llm_model": setting.model if setting else "",
        "llm_api_key_set": bool(setting and setting.api_key),
        # 服务端是否配了公共模型（用户未填 Key 时的兜底）
        "fallback_available": bool(global_settings.llm_api_key),
        "presets": PROVIDER_PRESETS,
    }


@router.put("/settings/provider")
async def update_provider_settings(
    body: ProviderSettings,
    request: Request,
    service: ServiceDep,
    user_id: UserIdDep,
    runtime: RuntimeDep,
):
    preset = PROVIDER_PRESETS.get(body.llm_provider)
    if body.llm_provider not in PROVIDER_PRESETS and body.llm_provider != "openai-compatible":
        raise AppError(
            "PROVIDER_NOT_SUPPORTED",
            f"不支持的模型服务: {body.llm_provider}",
            422,
            ErrorCategory.VALIDATION,
        )

    base_url = body.llm_base_url or (preset["base_url"] if preset else "")
    model = body.llm_model or (preset["model"] if preset else "")

    existing = await service.get_user_llm_setting(user_id)
    api_key = body.llm_api_key or (existing.api_key if existing else "")
    if not api_key:
        raise AppError(
            "API_KEY_REQUIRED",
            "请填写你的 API Key（只保存到你自己的账户，不会共享给其他用户）。",
            422,
            ErrorCategory.VALIDATION,
        )

    setting = await service.upsert_user_llm_setting(
        user_id, body.llm_provider, base_url, api_key, model
    )
    # 配置更新后清掉该用户的 provider 缓存，下一次对话立即用新 Key
    await runtime.invalidate_user_provider(user_id)

    return {
        "status": "saved",
        "message": "你的模型配置已保存，下次对话立即生效。",
        "llm_provider": setting.provider,
        "llm_api_key_set": bool(setting.api_key),
    }
