import asyncio

from app.application.keyed_lock import KeyedLockPool


def test_keyed_lock_pool_reclaims_entries_after_use():
    async def scenario():
        pool = KeyedLockPool()
        order: list[int] = []

        async def worker(index: int):
            async with pool.hold("shared"):
                order.append(index)
                await asyncio.sleep(0)

        await asyncio.gather(*(worker(index) for index in range(5)))
        assert order == list(range(5))
        assert pool.size() == 0

    asyncio.run(scenario())
