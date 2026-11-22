"""匿名多用户会话：cookie 识别用户、数据隔离、onboarding 流程。"""

from fastapi.testclient import TestClient

from app.core.user_session import COOKIE_NAME


def _fresh_client(app):
    """不带预设 cookie 的全新客户端（模拟新访客浏览器）。"""
    return TestClient(app)


def test_new_visitor_gets_user_cookie(app):
    """首次访问：自动种签名 cookie，/me 返回未完成引导的新用户。"""
    with _fresh_client(app) as visitor:
        response = visitor.get("/api/v1/me")
        assert response.status_code == 200
        body = response.json()
        assert body["onboarded"] is False
        assert body["display_name"] == ""
        assert COOKIE_NAME in visitor.cookies


def test_same_visitor_keeps_identity(app):
    """同一浏览器（cookie 保持）：多次请求 user_id 稳定。"""
    with _fresh_client(app) as visitor:
        first = visitor.get("/api/v1/me").json()
        second = visitor.get("/api/v1/me").json()
        assert first["user_id"] == second["user_id"]


def test_forged_cookie_is_rejected(app):
    """伪造 cookie（签名错误）：按新访客处理，不会冒充他人。"""
    with _fresh_client(app) as attacker:
        attacker.cookies.set(COOKIE_NAME, "some-victim-id.deadbeef")
        me = attacker.get("/api/v1/me").json()
        assert me["user_id"] != "some-victim-id"


def test_onboarding_sets_display_name(app):
    """引导：填写昵称后 onboarded 变为 true。"""
    with _fresh_client(app) as visitor:
        assert visitor.get("/api/v1/me").json()["onboarded"] is False
        response = visitor.patch(
            "/api/v1/me", json={"display_name": "小明"}
        )
        assert response.status_code == 200, response.text
        assert response.json()["onboarded"] is True
        assert visitor.get("/api/v1/me").json()["display_name"] == "小明"


def test_onboarding_empty_name_rejected(app):
    with _fresh_client(app) as visitor:
        response = visitor.patch("/api/v1/me", json={"display_name": "  "})
        assert response.status_code == 422


def test_visitors_data_isolated(app):
    """两个访客各自创建会话，互相看不到对方的数据。"""
    with _fresh_client(app) as alice:
        alice.patch("/api/v1/me", json={"display_name": "Alice"})
        conv = alice.post(
            "/api/v1/conversations", json={"title": "Alice 的会话"}
        ).json()

    with _fresh_client(app) as bob:
        # Bob 看不到 Alice 的会话
        assert bob.get(f"/api/v1/conversations/{conv['id']}").status_code == 404
        # Bob 有自己的独立会话列表
        bob.post("/api/v1/conversations", json={"title": "Bob 的会话"})
        bob_titles = [c["title"] for c in bob.get("/api/v1/conversations").json()]
        assert bob_titles == ["Bob 的会话"]
        assert "Alice 的会话" not in bob_titles


def test_user_llm_settings_are_per_user(app):
    """模型配置按用户隔离：各自保存各自的 Key，互不可见。"""
    with _fresh_client(app) as alice:
        response = alice.put(
            "/api/v1/settings/provider",
            json={"llm_provider": "modelscope", "llm_api_key": "alice-key"},
        )
        assert response.status_code == 200, response.text
        me = alice.get("/api/v1/settings/provider").json()
        assert me["llm_provider"] == "modelscope"
        assert me["llm_api_key_set"] is True
        # 不返回明文 Key
        assert "alice-key" not in response.text and "alice-key" not in str(me)

    with _fresh_client(app) as bob:
        me = bob.get("/api/v1/settings/provider").json()
        assert me["llm_api_key_set"] is False  # Bob 没配过，看不到 Alice 的


def test_user_llm_settings_requires_key(app):
    """没有全局兜底 Key 时，用户保存配置必须填 Key。"""
    with _fresh_client(app) as visitor:
        response = visitor.put(
            "/api/v1/settings/provider",
            json={"llm_provider": "modelscope", "llm_api_key": ""},
        )
        assert response.status_code == 422


def test_user_llm_settings_invalidate_provider_cache(app):
    """保存配置后，runtime 中该用户的 provider 缓存被清理。"""
    with _fresh_client(app) as visitor:
        visitor.put(
            "/api/v1/settings/provider",
            json={"llm_provider": "modelscope", "llm_api_key": "key-1"},
        )
        user_id = visitor.get("/api/v1/me").json()["user_id"]
        runtime = app.state.runtime
        # 模拟已有缓存（真实场景由 resolve_user_provider 写入）
        runtime._user_providers[user_id] = object()
        # 再次保存配置（换成自定义兼容服务），缓存应被清掉
        visitor.put(
            "/api/v1/settings/provider",
            json={
                "llm_provider": "openai-compatible",
                "llm_api_key": "key-2",
                "llm_base_url": "https://example.com/v1",
                "llm_model": "example-model",
            },
        )
        assert user_id not in runtime._user_providers
