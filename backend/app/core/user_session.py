"""匿名用户会话：签名 cookie 标识每个访客，实现多用户数据隔离。

不依赖 IP（NAT 下多人同 IP、换网即变），首次访问自动生成匿名用户并
通过 HMAC 签名 cookie 记住（防伪造），后续请求按 cookie 归属数据。
"""

from __future__ import annotations

import hashlib
import hmac
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

COOKIE_NAME = "yb_uid"
COOKIE_MAX_AGE = 365 * 24 * 3600  # 一年


def _sign(value: str, secret: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def make_user_cookie(user_id: str, secret: str) -> str:
    """签发 `user_id.hmac` 格式的 cookie 值（测试和调试也可用）。"""
    return f"{user_id}.{_sign(user_id, secret)}"


def parse_user_cookie(value: str | None, secret: str) -> str | None:
    """校验签名并返回 user_id；无效或缺失返回 None。"""
    if not value or "." not in value:
        return None
    user_id, _, signature = value.rpartition(".")
    if not user_id:
        return None
    if hmac.compare_digest(signature, _sign(user_id, secret)):
        return user_id
    return None


class UserSessionMiddleware(BaseHTTPMiddleware):
    """为 /api 请求解析（或创建）匿名用户，并种下签名 cookie。"""

    def __init__(self, app, *, secret: str, users_service, timezone: str):
        super().__init__(app)
        self.secret = secret
        self.users_service = users_service
        self.timezone = timezone
        # 已确认存在于 users 表的 user_id 缓存，避免每请求查库
        self._known: set[str] = set()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path == "/api" or path.startswith("/api/"):
            user_id = parse_user_cookie(request.cookies.get(COOKIE_NAME), self.secret)
            if user_id is None or user_id not in self._known:
                verified = False
                if user_id is not None:
                    verified = await self.users_service.exists(user_id)
                    if verified:
                        self._known.add(user_id)
                if not verified:
                    user_id = str(uuid.uuid4())
                    await self.users_service.ensure_user(user_id, self.timezone)
                    self._known.add(user_id)
                request.state.user_id = user_id
            else:
                request.state.user_id = user_id
            response = await call_next(request)
            response.set_cookie(
                COOKIE_NAME,
                make_user_cookie(user_id, self.secret),
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax",
                path="/",
            )
            return response
        return await call_next(request)
