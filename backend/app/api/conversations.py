from fastapi import APIRouter

from app.api.dependencies import RuntimeDep, ServiceDep, UserIdDep
from app.schemas.conversations import (
    ConversationCreate,
    ConversationDetail,
    ConversationPatch,
    ConversationRead,
    MessageCreate,
    MessageRead,
    RunAccepted,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationRead, status_code=201)
async def create_conversation(
    service: ServiceDep,
    user_id: UserIdDep,
    body: ConversationCreate | None = None,
):
    title = body.title if body else ""
    is_group = body.is_group if body else False
    persona_ids = body.persona_ids if body else None
    conv = await service.create_conversation(user_id, title, is_group=is_group, persona_ids=persona_ids)
    if is_group and persona_ids:
        names = "、".join(p.get("name", "?") for p in persona_ids)
        await service.add_message(
            user_id, conv.id, "system", f"🎉 {names} 加入了「{title}」群聊",
            persona_name="system",
        )
    return conv


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    service: ServiceDep,
    user_id: UserIdDep,
):
    return await service.list_conversations(user_id)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    service: ServiceDep,
    user_id: UserIdDep,
):
    conversation, messages = await service.get_conversation_with_messages(user_id, conversation_id)
    result = ConversationRead.model_validate(conversation).model_dump()
    result["messages"] = [MessageRead.model_validate(message) for message in messages]
    return result


@router.patch("/{conversation_id}", response_model=ConversationRead)
async def patch_conversation(
    conversation_id: str,
    body: ConversationPatch,
    service: ServiceDep,
    user_id: UserIdDep,
):
    return await service.patch_conversation(user_id, conversation_id, body.title)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    service: ServiceDep,
    user_id: UserIdDep,
):
    await service.delete_conversation(user_id, conversation_id)


@router.post("/{conversation_id}/messages", response_model=RunAccepted, status_code=202)
async def send_message(
    conversation_id: str,
    body: MessageCreate,
    runtime: RuntimeDep,
    user_id: UserIdDep,
):
    persona = None
    if body.persona:
        persona = {
            "name": body.persona.name,
            "style": body.persona.style,
            "traits": body.persona.traits,
            "address_user": body.persona.addressUser,
            "model": body.persona.model,
        }
    return await runtime.start(
        conversation_id, body.content, user_id,
        persona=persona,
        target_persona=body.target_persona,
        reply_to_id=body.reply_to_id,
    )


@router.post("/{conversation_id}/personas")
async def add_persona_to_group(
    conversation_id: str,
    body: dict,
    service: ServiceDep,
    user_id: UserIdDep,
):
    conv = await service.get_conversation(user_id, conversation_id)
    current = conv.persona_ids or []
    current.append(body)
    await service.patch_conversation(user_id, conversation_id, title=None, persona_ids=current)
    name = body.get("name", "新成员")
    await service.add_message(
        user_id, conversation_id, "system", f"📢 {name} 加入了群聊",
        persona_name="system",
    )
    return {"status": "ok", "persona_ids": current}


@router.patch("/{conversation_id}/personas/{persona_name}")
async def update_persona_in_group(
    conversation_id: str,
    persona_name: str,
    body: dict,
    service: ServiceDep,
    user_id: UserIdDep,
):
    conv = await service.get_conversation(user_id, conversation_id)
    current = conv.persona_ids or []
    editable = {"name", "style", "traits", "addressUser", "avatar", "model", "max_replies"}
    updated = False
    for p in current:
        if p.get("name") == persona_name:
            for key, value in body.items():
                if key in editable and value is not None:
                    p[key] = value
            updated = True
            break
    if not updated:
        from app.core.errors import AppError, ErrorCategory

        raise AppError(
            "PERSONA_NOT_FOUND",
            f"会话中不存在人格：{persona_name}",
            404,
            ErrorCategory.NOT_FOUND,
        )
    await service.patch_conversation(user_id, conversation_id, title=None, persona_ids=current)
    if "max_replies" in body:
        await service.add_message(
            user_id, conversation_id, "system",
            f"⚙️ {body.get('name', persona_name)} 的自动回复轮次已调整为 {body['max_replies']} 轮",
            persona_name="system",
        )
    else:
        await service.add_message(
            user_id, conversation_id, "system",
            f"🔧 {body.get('name', persona_name)} 的人格设定已更新",
            persona_name="system",
        )
    return {"status": "ok", "persona_ids": current}
