import uuid
from pathlib import Path

ALLOWED_MIMES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
EXTENSION_MAP = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class FileStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def user_dir(self, user_id: str) -> Path:
        d = self.base_dir / user_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def save_upload(
        self, user_id: str, data: bytes, content_type: str
    ) -> dict[str, str]:
        if content_type not in ALLOWED_MIMES:
            raise ValueError(f"不支持的文件类型: {content_type}")
        if len(data) > MAX_FILE_SIZE:
            raise ValueError(f"文件超过 {MAX_FILE_SIZE // (1024*1024)}MB 限制")

        ext = EXTENSION_MAP[content_type]
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{ext}"
        path = self.user_dir(user_id) / filename
        path.write_bytes(data)

        return {
            "file_id": file_id,
            "path": str(path),
            "url": f"/uploads/{user_id}/{filename}",
            "mime": content_type,
        }

    def get_path(self, relative_url: str) -> Path | None:
        path = self.base_dir / relative_url.removeprefix("/uploads/")
        if path.exists():
            return path
        return None
