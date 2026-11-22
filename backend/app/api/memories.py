from fastapi import APIRouter
from pydantic import BaseModel

from app.api.dependencies import ServiceDep, UserIdDep
from app.schemas.memories import MemoryCreate, MemoryRead

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("", response_model=list[MemoryRead])
async def list_memories(
    service: ServiceDep,
    user_id: UserIdDep,
):
    return await service.list_memories(user_id)


@router.post("", response_model=MemoryRead, status_code=201)
async def create_memory(
    body: MemoryCreate,
    service: ServiceDep,
    user_id: UserIdDep,
):
    return await service.create_memory(user_id, body.content, body.type, body.subject)


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: str,
    service: ServiceDep,
    user_id: UserIdDep,
):
    await service.memories.delete(user_id, memory_id)


class MemoryPatch(BaseModel):
    content: str


@router.patch("/{memory_id}")
async def update_memory(
    memory_id: str,
    body: MemoryPatch,
    service: ServiceDep,
    user_id: UserIdDep,
):
    memory = await service.memories.update(user_id, memory_id, body.content)
    return {"id": memory.id, "content": memory.content, "type": memory.type}


@router.get("/graph")
async def get_memory_graph(
    service: ServiceDep,
    user_id: UserIdDep,
):
    return await service.memories.get_graph(user_id)
