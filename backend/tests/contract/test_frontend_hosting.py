import pytest

from app.core.config import MISSION_DIR


def test_root_and_spa_routes_serve_an_html_shell(client):
    root = client.get("/")
    assert root.status_code == 200
    assert "text/html" in root.headers["content-type"]

    deep_link = client.get("/memories")
    assert deep_link.status_code == 200
    assert deep_link.text == root.text


def test_unknown_api_route_keeps_json_error_contract(client):
    response = client.get("/api/v1/not-a-real-route")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "API_ROUTE_NOT_FOUND"


def test_react_build_asset_is_served_when_dist_exists(client):
    if not (MISSION_DIR / "frontend" / "dist" / "index.html").exists():
        pytest.skip("frontend dist is not built in backend-only test jobs")
    index = client.get("/").text
    marker = 'src="/assets/'
    assert marker in index
    asset_path = "/assets/" + index.split(marker, 1)[1].split('"', 1)[0]
    response = client.get(asset_path)
    assert response.status_code == 200
