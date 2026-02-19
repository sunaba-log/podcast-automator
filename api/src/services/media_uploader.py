from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from src.config import get_settings
from src.errors import AppError
from src.services.r2_client import R2Client

IMAGE_TYPES = {"image/png", "image/jpeg"}
AUDIO_TYPES = {"audio/mpeg", "audio/mp4"}
UPLOAD_DIR = Path("api/data/uploads")


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _build_key(owner_id: str, filename: str) -> str:
    suffix = Path(filename).suffix or ""
    return f"media/{owner_id}/{uuid4().hex}{suffix}"


def _public_url(key: str) -> str:
    settings = get_settings()
    if settings.r2_public_base_url:
        return f"{settings.r2_public_base_url.rstrip('/')}/{key}"
    return str(UPLOAD_DIR / key)


def upload_image(owner_id: str, filename: str, content_type: str, data: bytes) -> str:
    if content_type not in IMAGE_TYPES:
        raise AppError("画像形式が不正です", status_code=400)
    key = _build_key(owner_id, filename)
    # local_path = UPLOAD_DIR / key
    # _ensure_dir(local_path)
    # local_path.write_bytes(data)
    R2Client().upload_bytes(key, data, content_type)
    return _public_url(key)


def upload_audio(owner_id: str, filename: str, content_type: str, data: bytes) -> tuple[str, int]:
    if content_type not in AUDIO_TYPES:
        raise AppError("音声形式が不正です", status_code=400)
    key = _build_key(owner_id, filename)
    # local_path = UPLOAD_DIR / key
    # _ensure_dir(local_path)
    # local_path.write_bytes(data)
    R2Client().upload_bytes(key, data, content_type)
    return _public_url(key), len(data)
