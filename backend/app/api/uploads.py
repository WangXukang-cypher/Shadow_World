import base64

from fastapi import APIRouter, Request, UploadFile

from app.core.errors import AppError, ErrorCategory
from app.infrastructure.file_store import ALLOWED_MIMES, MAX_FILE_SIZE

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("")
async def upload_file(request: Request, file: UploadFile):
    if file.content_type not in ALLOWED_MIMES:
        raise AppError(
            "UPLOAD_INVALID_TYPE",
            f"不支持的文件类型，仅支持：{', '.join(ALLOWED_MIMES)}",
            400,
            ErrorCategory.VALIDATION,
        )
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise AppError(
            "UPLOAD_TOO_LARGE",
            f"文件超过 {MAX_FILE_SIZE // (1024*1024)}MB 限制。",
            400,
            ErrorCategory.VALIDATION,
        )

    file_store = request.app.state.file_store
    user_id = request.state.user_id
    result = await file_store.save_upload(user_id, data, file.content_type)
    result["base64"] = base64.b64encode(data).decode()
    return result
