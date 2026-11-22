from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_mock_memory_flow(tmp_path):
    app = create_app(Settings(database_path=str(tmp_path / "api.db"), reminder_poll_seconds=0.05))
    with TestClient(app) as client:
        conversation = client.post("/api/v1/conversations").json()
        response = client.post(
            f"/api/v1/conversations/{conversation['id']}/messages",
            json={"content": "记住我喜欢简短回答"},
        )
        assert response.status_code == 202
        run_id = response.json()["id"]
        with client.stream("GET", f"/api/v1/runs/{run_id}/events") as stream:
            body = "".join(stream.iter_text())
        assert "run.completed" in body
        assert run_id not in app.state.runtime._queues
        memories = client.get("/api/v1/memories").json()
        assert [item["content"] for item in memories] == ["我喜欢简短回答"]
