from fastapi import APIRouter

from app.api.dependencies import ServiceDep, UserIdDep
from app.schemas.tasks import TaskCreate, TaskRead

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
async def list_tasks(
    service: ServiceDep,
    user_id: UserIdDep,
):
    return await service.list_tasks(user_id)


@router.post("", response_model=TaskRead, status_code=201)
async def create_task(
    body: TaskCreate,
    service: ServiceDep,
    user_id: UserIdDep,
):
    return await service.create_task(user_id, body.title, body.remind_at, body.due_at)


@router.post("/{task_id}/complete", status_code=200)
async def complete_task(
    task_id: str,
    service: ServiceDep,
    user_id: UserIdDep,
):
    task = await service.tasks.complete(user_id, task_id)
    return {"id": task.id, "status": task.status}


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    service: ServiceDep,
    user_id: UserIdDep,
):
    await service.tasks.delete(user_id, task_id)
