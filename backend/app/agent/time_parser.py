import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo


def parse_mock_reminder(text: str, timezone_name: str) -> datetime | None:
    match = re.search(r"(?:(今天|明天|后天)\s*)?(\d{1,2})[:：](\d{2})", text)
    if match is None:
        return None
    day_word, hour_text, minute_text = match.groups()
    hour, minute = int(hour_text), int(minute_text)
    if hour > 23 or minute > 59:
        return None
    local_now = datetime.now(ZoneInfo(timezone_name))
    offset = {None: 0, "今天": 0, "明天": 1, "后天": 2}[day_word]
    candidate = (local_now + timedelta(days=offset)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    if day_word is None and candidate <= local_now:
        candidate += timedelta(days=1)
    return candidate.astimezone(UTC)
