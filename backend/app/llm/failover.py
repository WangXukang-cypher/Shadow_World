import logging
from collections.abc import AsyncIterator

from .base import LLMProvider
from .models import LLMEvent, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class FailoverProvider:
    """Wraps a primary provider with retry and optional fallback."""

    name = "failover"

    def __init__(
        self,
        primary: LLMProvider,
        fallback: LLMProvider | None = None,
        max_retries: int = 2,
    ):
        self.primary = primary
        self.fallback = fallback
        self.max_retries = max_retries

    async def create_response(self, request: LLMRequest) -> LLMResponse:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return await self.primary.create_response(request)
            except Exception as exc:  # noqa: BLE001 - retry all provider failures
                last_error = exc
                logger.warning(
                    "Provider %s failed (attempt %d/%d): %s",
                    self.primary.name,
                    attempt + 1,
                    self.max_retries + 1,
                    type(exc).__name__,
                )
        if self.fallback:
            logger.info("Switching to fallback provider: %s", self.fallback.name)
            try:
                return await self.fallback.create_response(request)
            except Exception as exc:
                logger.error("Fallback provider also failed: %s", type(exc).__name__)
                raise exc from last_error
        raise last_error  # type: ignore[misc]

    def stream_response(self, request: LLMRequest) -> AsyncIterator[LLMEvent]:
        return self.primary.stream_response(request)
