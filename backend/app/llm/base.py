from collections.abc import AsyncIterator
from typing import Protocol

from .models import LLMEvent, LLMRequest, LLMResponse


class LLMProvider(Protocol):
    name: str

    async def create_response(self, request: LLMRequest) -> LLMResponse: ...

    def stream_response(self, request: LLMRequest) -> AsyncIterator[LLMEvent]: ...
