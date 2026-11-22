from datetime import datetime
from typing import Any

from .common import ORMModel


class NotificationRead(ORMModel):
    id: int
    user_id: str
    type: str
    payload: dict[str, Any]
    created_at: datetime
    read_at: datetime | None
