import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import ApiSettings
from app.schemas.settings import SettingsUpdate, TestResult
from app.services.crypto import decrypt, encrypt, get_secret

router = APIRouter(prefix="/api/settings", tags=["settings"])

REQUIRED_KEYS = [
    ("dashscope_api_key", True),
    ("dashscope_workspace_id", False),
    ("deepseek_api_key", True),
    ("paddleocr_cloud_key", False),
    ("ytdlp_cookie_path", False),
]


def _from_env(key: str) -> bool:
    """该 key 是否由环境变量 SMART_SCRIBE_<KEY_UPPER> 提供。"""
    return bool(os.environ.get(f"SMART_SCRIBE_{key.upper()}"))


@router.get("")
async def list_settings(db: Session = Depends(get_db)):
    result = []
    for key, required in REQUIRED_KEYS:
        existing = db.query(ApiSettings).filter_by(key=key).first()
        from_env = _from_env(key)
        # is_set：DB 有 或 环境变量有 都算已配置
        result.append({
            "key": key,
            "is_set": existing is not None or from_env,
            "is_required": required,
            "from_env": from_env,
        })
    return result


@router.post("")
async def update_settings(body: SettingsUpdate, db: Session = Depends(get_db)):
    for item in body.settings:
        existing = db.query(ApiSettings).filter_by(key=item.key).first()
        enc = encrypt(item.value)
        if existing:
            existing.encrypted_value = enc
            existing.is_required = item.is_required
        else:
            db.add(ApiSettings(key=item.key, encrypted_value=enc, is_required=item.is_required))
    db.commit()
    return {"status": "ok"}


@router.post("/{key}/test")
async def test_setting(key: str, db: Session = Depends(get_db)):
    existing = db.query(ApiSettings).filter_by(key=key).first()
    if not existing or not existing.encrypted_value:
        return TestResult(key=key, ok=False, message="未配置")
    try:
        plaintext = decrypt(existing.encrypted_value)
    except Exception:
        return TestResult(key=key, ok=False, message="解密失败")
    if not plaintext:
        return TestResult(key=key, ok=False, message="值为空")
    return TestResult(key=key, ok=True, message="格式有效")


from app.config import get_settings


@router.get("/ocr-mode")
async def get_ocr_mode():
    return {"mode": get_settings().ocr_mode, "note": "通过环境变量 SMART_SCRIBE_OCR_MODE 配置，需重启生效"}


@router.get("/ephemeral")
async def get_ephemeral():
    s = get_settings()
    return {
        "enabled": s.ephemeral,
        "ttl": s.ephemeral_ttl,
        "note": "用完即焚：生成总结后将自动删除该会话的所有媒体与记录" if s.ephemeral else "",
    }