import hashlib
import json


def build_idempotency_key(
    user_id: str,
    source_message_id: str,
    tool_name: str,
    arguments: dict,
) -> str:
    """Deduplicates retries within one user request, not future intentional requests."""
    canonical = json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    raw = f"{user_id}:{source_message_id}:{tool_name}:{canonical}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
