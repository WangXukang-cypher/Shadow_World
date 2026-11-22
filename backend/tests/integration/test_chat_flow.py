def test_mock_memory_flow_and_event_replay(client):
    conversation = client.post("/api/v1/conversations", json={}).json()
    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"content": "记住我喜欢简短回答"},
    )
    assert response.status_code == 202
    run_id = response.json()["id"]

    with client.stream("GET", f"/api/v1/runs/{run_id}/events") as stream:
        body = "".join(stream.iter_text())
    assert "event: memory.saved" in body
    assert "event: run.completed" in body

    replay = client.get(f"/api/v1/runs/{run_id}/events").text
    assert "event: run.completed" in replay
    memories = client.get("/api/v1/memories").json()
    assert [item["content"] for item in memories] == ["我喜欢简短回答"]
    run_detail = client.get(f"/api/v1/runs/{run_id}").json()
    assert run_detail["model_name"] == "mock"
    assert run_detail["iteration_count"] == 2
    assert run_detail["tool_calls"][0]["tool_name"] == "create_memory"
    assert run_detail["tool_calls"][0]["status"] == "completed"

    detail = client.get(f"/api/v1/conversations/{conversation['id']}").json()
    assert [item["seq"] for item in detail["messages"]] == [1, 2]


def test_create_task_flow(client):
    conversation = client.post("/api/v1/conversations", json={}).json()
    run = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"content": "提醒我明天 10:00 交周报"},
    ).json()
    with client.stream("GET", f"/api/v1/runs/{run['id']}/events") as stream:
        body = "".join(stream.iter_text())
    assert "event: tool.finished" in body
    tasks = client.get("/api/v1/tasks").json()
    assert len(tasks) == 1
    assert tasks[0]["remind_at"] is not None


def test_run_sse_subscribes_before_history_query(app, client, monkeypatch):
    conversation = client.post("/api/v1/conversations", json={}).json()
    run = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"content": "你好"},
    ).json()
    service = app.state.service
    original = service.list_run_events
    subscribed = False

    def subscribe(run_id):
        nonlocal subscribed
        subscribed = True
        return app.state.broker.__class__.subscribe_run(app.state.broker, run_id)

    async def checked_history(user_id, run_id, after_seq=0):
        assert subscribed is True
        return await original(user_id, run_id, after_seq)

    monkeypatch.setattr(app.state.broker, "subscribe_run", subscribe)
    monkeypatch.setattr(service, "list_run_events", checked_history)
    with client.stream("GET", f"/api/v1/runs/{run['id']}/events") as stream:
        body = "".join(stream.iter_text())
    assert "event: run.completed" in body
