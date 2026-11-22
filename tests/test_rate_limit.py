import asyncio

from app.rate_limit import RunLimiter


def test_cleanup_removes_inactive_user_buckets():
    async def scenario():
        limiter = RunLimiter(per_user=1, global_limit=1, per_minute=2, window_seconds=0)
        await limiter.reserve("user")
        await limiter.release("user", global_acquired=False)
        await limiter.cleanup_expired()
        assert "user" not in limiter._submissions
        assert "user" not in limiter._per_user_reserved

    asyncio.run(scenario())
