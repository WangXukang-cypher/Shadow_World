import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.application.services import DEFAULT_USER_ID
from app.bootstrap import build_container
from app.core.config import MISSION_DIR, Settings, get_settings
from app.core.errors import AppError, ErrorCategory, install_error_handlers
from app.core.request_context import RequestContextMiddleware
from app.core.user_session import UserSessionMiddleware
from app.infrastructure.db.base import Base
from app.infrastructure.file_store import FileStore

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()
    container = build_container(cfg)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if cfg.auto_create_schema:
            async with container.engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        # 清理上次进程遗留的僵尸 run（重启时仍在执行的任务已随进程消失）
        stale_count = await container.service.fail_stale_runs()
        if stale_count:
            logger.warning("marked %d stale run(s) as failed on startup", stale_count)
        await container.service.ensure_default_user(cfg.timezone)
        reminder_task = asyncio.create_task(container.reminder_worker.run())
        try:
            yield
        finally:
            container.reminder_worker.stop()
            await reminder_task
            close_provider = getattr(container.provider, "close", None)
            if close_provider is not None:
                await close_provider()
            await container.engine.dispose()

    app = FastAPI(title="Memento Assistant API", version="0.2.0", lifespan=lifespan)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        UserSessionMiddleware,
        secret=cfg.session_secret,
        users_service=container.service.users,
        timezone=cfg.timezone,
    )
    install_error_handlers(app)
    app.include_router(api_router)

    app.state.settings = cfg
    app.state.container = container
    app.state.engine = container.engine
    app.state.sessions = container.sessions
    app.state.service = container.service
    app.state.broker = container.broker
    app.state.runtime = container.runtime
    app.state.default_user_id = DEFAULT_USER_ID
    app.state.file_store = FileStore(MISSION_DIR / "data" / "uploads")

    frontend_dist = MISSION_DIR / "frontend" / "dist"
    legacy_static = MISSION_DIR / "app" / "static"
    static_dir = frontend_dist if (frontend_dist / "index.html").exists() else legacy_static
    if static_dir.exists():
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

        @app.get("/", include_in_schema=False)
        async def index():
            return FileResponse(Path(static_dir) / "index.html")

        @app.get("/{spa_path:path}", include_in_schema=False)
        async def spa_fallback(spa_path: str):
            if spa_path == "api" or spa_path.startswith("api/"):
                raise AppError(
                    "API_ROUTE_NOT_FOUND",
                    "接口不存在。",
                    404,
                    ErrorCategory.NOT_FOUND,
                )
            requested = static_dir / spa_path
            if requested.is_file():
                return FileResponse(requested)
            return FileResponse(Path(static_dir) / "index.html")

    return app


app = create_app()
