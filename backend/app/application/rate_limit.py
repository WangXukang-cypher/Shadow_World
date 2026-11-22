import asyncio
import time
from collections import defaultdict, deque

from app.core.errors import AppError, ErrorCategory


class RunLimiter:
    def __init__(self, per_user: int, global_limit: int, per_minute: int):
        self._global = asyncio.Semaphore(global_limit)
        self._per_user_limit = per_user
        self._per_user_active: dict[str, int] = defaultdict(int)
        self._submissions: dict[str, deque[float]] = defaultdict(deque)
        self._per_minute = per_minute
        self._lock = asyncio.Lock()

    async def reserve(self, user_id: str) -> None:
        now = time.monotonic()
        async with self._lock:
            bucket = self._submissions[user_id]
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            if len(bucket) >= self._per_minute:
                raise AppError(
                    "MESSAGE_RATE_LIMITED",
                    "请求过于频繁，请稍后再试。",
                    429,
                    ErrorCategory.RATE_LIMIT,
                )
            if self._per_user_active[user_id] >= self._per_user_limit:
                raise AppError(
                    "TOO_MANY_ACTIVE_RUNS",
                    "当前已有任务正在运行，请稍后再试。",
                    429,
                    ErrorCategory.RATE_LIMIT,
                )
            bucket.append(now)
            self._per_user_active[user_id] += 1

    async def acquire_global(self) -> None:
        await self._global.acquire()

    async def release(self, user_id: str, global_acquired: bool) -> None:
        async with self._lock:
            remaining = max(0, self._per_user_active.get(user_id, 0) - 1)
            if remaining:
                self._per_user_active[user_id] = remaining
            else:
                self._per_user_active.pop(user_id, None)
        if global_acquired:
            self._global.release()
