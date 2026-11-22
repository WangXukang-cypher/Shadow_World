# Shadow World Backend

Shadow World 的后端服务，基于 FastAPI、SQLAlchemy Async、SQLite 和 Alembic。项目总览、完整配置与启动方式请先阅读根目录 [README](../README.md)。

## 主要模块

- `app/agent`：Agent Runtime、上下文构建、流式事件与 Tool Loop。
- `app/api`：版本化 REST API，统一使用 `/api/v1` 前缀。
- `app/application`：会话、记忆、待办、人物、技能和运行记录等应用服务。
- `app/llm`：Mock、OpenAI-compatible 与故障降级 Provider。
- `app/tools`：记忆、待办、人物、技能、搜索和时间工具。
- `app/notifications`：提醒 Worker 与通知事件流。
- `alembic`：显式数据库迁移。
- `tests`：单元、集成和 API 契约测试。

## 开发

在仓库根目录准备 `.env` 后运行：

```bash
cd backend
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

服务默认监听 <http://127.0.0.1:8000>，交互式 API 文档位于 <http://127.0.0.1:8000/docs>。

## 检查

```bash
uv run ruff check .
uv run pytest -q
uv run python scripts/export_openapi.py openapi.json
```

数据库结构发生变化时必须新增显式 Alembic revision，不要依赖 `create_all()` 代替增量迁移。

## 导入旧版数据

先执行 dry-run：

```bash
uv run python scripts/migrate_mvp_data.py \
  --source ../data/assistant.db \
  --target sqlite+aiosqlite:///../data/assistant-v1.db \
  --dry-run
```

确认后移除 `--dry-run` 并加上 `--backup`。脚本不会删除源数据库。
