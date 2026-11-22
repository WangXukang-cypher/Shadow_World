import asyncio
import threading

from app.async_db import AsyncDatabase


class _SlowDatabase:
    def list_memories(self, user_id):
        del user_id
        threading.Event().wait(0.05)
        return []


def test_async_database_does_not_block_event_loop():
    async def scenario():
        database = AsyncDatabase(_SlowDatabase())  # type: ignore[arg-type]
        heartbeat_ran = False

        async def heartbeat():
            nonlocal heartbeat_ran
            await asyncio.sleep(0.005)
            heartbeat_ran = True

        await asyncio.gather(database.list_memories("user"), heartbeat())
        assert heartbeat_ran is True

    asyncio.run(scenario())
