import asyncio
import time
from collections import defaultdict, deque


class RateLimitExceeded(Exception):
    pass


class RunLimiter:
    def __init__(
        self, per_user: int, global_limit: int, per_minute: int, window_seconds: float = 60.0
    ):
        self._global = asyncio.Semaphore(global_limit)
        self._per_user_limit = per_user
        self._per_user_reserved: dict[str, int] = defaultdict(int)
        self._submissions: dict[str, deque[float]] = defaultdict(deque)
        self._per_minute = per_minute
        self._window_seconds = window_seconds
        self._lock = asyncio.Lock()

    def _prune_user(self, user_id: str, now: float) -> None:
        bucket = self._submissions.get(user_id)
        if bucket is not None:
            while bucket and bucket[0] <= now - self._window_seconds:
                bucket.popleft()
            if not bucket:
                self._submissions.pop(user_id, None)
        if self._per_user_reserved.get(user_id, 0) == 0:
            self._per_user_reserved.pop(user_id, None)

    async def reserve(self, user_id: str) -> None:
        now = time.monotonic()
        async with self._lock:
            self._prune_user(user_id, now)
            bucket = self._submissions.setdefault(user_id, deque())
            if len(bucket) >= self._per_minute:
                raise RateLimitExceeded("message rate limit exceeded")
            if self._per_user_reserved.get(user_id, 0) >= self._per_user_limit:
                raise RateLimitExceeded("too many active runs")
            bucket.append(now)
            self._per_user_reserved[user_id] = self._per_user_reserved.get(user_id, 0) + 1

    async def acquire_global(self) -> None:
        await self._global.acquire()

    async def release(self, user_id: str, global_acquired: bool = True) -> None:
        async with self._lock:
            remaining = max(0, self._per_user_reserved.get(user_id, 0) - 1)
            if remaining:
                self._per_user_reserved[user_id] = remaining
            else:
                self._per_user_reserved.pop(user_id, None)
            self._prune_user(user_id, time.monotonic())
        if global_acquired:
            self._global.release()

    async def cleanup_expired(self) -> None:
        now = time.monotonic()
        async with self._lock:
            user_ids = set(self._submissions) | set(self._per_user_reserved)
            for user_id in user_ids:
                self._prune_user(user_id, now)
