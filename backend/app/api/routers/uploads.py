import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile

from app.api.deps import require_staff

router = APIRouter(prefix="/uploads", tags=["uploads"], dependencies=[Depends(require_staff)])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Voice-note recordings from the browser only — shop photos still come from
# the scout bot as Telegram file_ids (see shops.py's /photo proxy).
ALLOWED_EXTENSIONS = {".webm", ".ogg", ".mp3", ".m4a", ".wav"}


@router.post("")
async def upload_file(file: UploadFile) -> dict[str, str]:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".webm"
    name = f"{uuid.uuid4().hex}{ext}"
    content = await file.read()
    (UPLOAD_DIR / name).write_bytes(content)
    return {"url": f"/uploads/{name}"}
