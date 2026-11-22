import hashlib
import re
import unicodedata

_SYNONYMS = (
    (re.compile(r"爱吃|喜欢吃"), "喜欢"),
    (re.compile(r"不爱吃|不喜欢吃"), "不喜欢"),
)


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\u4e00-\u9fff ]+", "", text)
    for pattern, replacement in _SYNONYMS:
        text = pattern.sub(replacement, text)
    return text.strip()


def memory_normalized_key(memory_type: str, subject: str, content: str) -> str:
    canonical = ":".join(
        (normalize_text(memory_type), normalize_text(subject), normalize_text(content))
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
