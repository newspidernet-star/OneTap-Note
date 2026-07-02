import shutil
from pathlib import Path
from fastapi import UploadFile

from app.config import get_settings

VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def classify_media(filename: str, content_type: str = "") -> str:
    ext = Path(filename).suffix.lower()
    if ext in VIDEO_EXTS or content_type.startswith("video/"):
        return "video"
    if ext in AUDIO_EXTS or content_type.startswith("audio/"):
        return "audio"
    if ext in IMAGE_EXTS or content_type.startswith("image/"):
        return "image"
    return "unknown"


def session_storage_dir(session_id: int) -> Path:
    settings = get_settings()
    d = settings.storage_dir / f"session_{session_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_upload(file: UploadFile, session_id: int) -> str:
    d = session_storage_dir(session_id)
    dest = d / Path(file.filename).name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return str(dest)


def resolve_storage_path(file_path: str) -> str:
    p = Path(file_path)
    if p.is_absolute():
        return str(p)

    storage_dir = get_settings().storage_dir
    try:
        p.relative_to(storage_dir)
        return str(p)
    except ValueError:
        pass

    if p.exists():
        return str(p)
    return str(storage_dir / p)
