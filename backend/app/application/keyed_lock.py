import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass
class _LockEntry:
    lock: asyncio.Lock
    references: int = 0


class KeyedLockPool:
    """Per-key asyncio locks that are removed after the last waiter leaves."""

    def __init__(self):
        self._entries: dict[str, _LockEntry] = {}
        self._guard = asyncio.Lock()

    @asynccontextmanager
    async def hold(self, key: str) -> AsyncIterator[None]:
        async with self._guard:
            entry = self._entries.get(key)
            if entry is None:
                entry = _LockEntry(lock=asyncio.Lock())
                self._entries[key] = entry
            entry.references += 1
        try:
            async with entry.lock:
                yield
        finally:
            async with self._guard:
                entry.references -= 1
                if entry.references == 0 and not entry.lock.locked():
                    self._entries.pop(key, None)

    def size(self) -> int:
        return len(self._entries)
