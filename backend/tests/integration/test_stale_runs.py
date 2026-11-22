import asyncio

from app.application.services import DEFAULT_USER_ID


def _seed_stale_run(service):
    """直接在 DB 中制造一个 running 状态但没有执行任务的僵尸 run。"""

    async def scenario():
        conv = await service.create_conversation(DEFAULT_USER_ID, "僵尸 run 测试")
        msg = await service.add_message(DEFAULT_USER_ID, conv.id, "user", "hi")
        run = await service.create_run(DEFAULT_USER_ID, conv.id, msg.id)
        await service.set_run_status(run.id, "running", "chat")
        return run

    return asyncio.run(scenario())


def test_fail_stale_runs_marks_non_terminal_runs(app, client):
    """fail_stale_runs 应把 running 的 run 标记为 failed。"""
    service = app.state.service
    run = _seed_stale_run(service)

    detail = client.get(f"/api/v1/runs/{run.id}").json()
    assert detail["status"] == "running"

    stale_count = asyncio.run(service.fail_stale_runs())
    assert stale_count == 1
    detail = client.get(f"/api/v1/runs/{run.id}").json()
    assert detail["status"] == "failed"
    assert detail["error_code"] == "RUN_STALE"

    # 已终态的 run 不会被再次清理
    assert asyncio.run(service.fail_stale_runs()) == 0


def test_startup_clears_stale_runs(app, client):
    """服务启动时自动清理僵尸 run（lifespan 中调用）。"""
    service = app.state.service
    run = _seed_stale_run(service)
    assert client.get(f"/api/v1/runs/{run.id}").json()["status"] == "running"

    # 模拟重启：同一 app 实例再次进入 lifespan，僵尸 run 应被标记为 failed
    with client:
        assert client.get(f"/api/v1/runs/{run.id}").json()["status"] == "failed"


def test_sse_stream_heals_stale_run(app, client):
    """SSE 连接到僵尸 run 时应补发 run.failed 终止事件。"""
    service = app.state.service
    run = _seed_stale_run(service)

    # 用流式请求读取 SSE，应收到自愈的 run.failed 事件
    lines = []
    with client.stream("GET", f"/api/v1/runs/{run.id}/events") as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            lines.append(line)
            if "RUN_STALE" in line:
                break

    text = "\n".join(lines)
    assert "run.failed" in text
    assert "RUN_STALE" in text

    detail = client.get(f"/api/v1/runs/{run.id}").json()
    assert detail["status"] == "failed"
    assert detail["error_code"] == "RUN_STALE"
