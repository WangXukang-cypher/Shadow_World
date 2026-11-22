def test_openapi_contains_stable_v1_routes(client):
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    required = {
        "/api/v1/conversations",
        "/api/v1/conversations/{conversation_id}",
        "/api/v1/conversations/{conversation_id}/messages",
        "/api/v1/runs/{run_id}",
        "/api/v1/runs/{run_id}/events",
        "/api/v1/memories",
        "/api/v1/tasks",
        "/api/v1/notifications",
        "/api/v1/notifications/stream",
        "/api/v1/health",
    }
    assert required <= set(paths)


def test_errors_use_stable_envelope(client):
    response = client.get("/api/v1/conversations/not-found")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "CONVERSATION_NOT_FOUND"
    assert body["error"]["request_id"]
    assert response.headers["x-request-id"] == body["error"]["request_id"]


def test_validation_errors_use_stable_envelope(client):
    conversation = client.post("/api/v1/conversations").json()
    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"content": ""},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"


def test_legacy_frontend_can_create_conversation_without_body(client):
    response = client.post("/api/v1/conversations")
    assert response.status_code == 201
    assert response.json()["title"] == ""
