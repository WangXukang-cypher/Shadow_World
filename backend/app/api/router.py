from fastapi import APIRouter

from . import conversations, memories, notifications, people, runs, system, tasks, uploads

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(conversations.router)
api_router.include_router(runs.router)
api_router.include_router(memories.router)
api_router.include_router(tasks.router)
api_router.include_router(people.router)
api_router.include_router(notifications.router)
api_router.include_router(system.router)
api_router.include_router(uploads.router)
