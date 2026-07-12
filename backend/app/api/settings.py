import os

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import ApiSettings
from app.schemas.settings import SettingsUpdate, TestResult
from app.services.crypto import encrypt, get_secret
from app.services.summarizer import DEEPSEEK_MODEL, DEEPSEEK_URL

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
    plaintext = get_secret(db, key)
    if not plaintext:
        return TestResult(key=key, ok=False, message="未配置")
    return TestResult(key=key, ok=True, message="格式有效")


@router.post("/{key}/test-live")
async def test_setting_live(key: str, db: Session = Depends(get_db)):
    plaintext = get_secret(db, key)
    if not plaintext:
        return TestResult(key=key, ok=False, message="未配置")
    if key != "deepseek_api_key":
        return TestResult(key=key, ok=True, message="已保存")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                DEEPSEEK_URL,
                headers={"Authorization": f"Bearer {plaintext}", "Content-Type": "application/json"},
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 8,
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        body = e.response.text[:300]
        if e.response.status_code == 401:
            message = "DeepSeek API Key 无效或已删除，请重新保存新的 Key"
        elif e.response.status_code in {402, 429}:
            message = "DeepSeek 额度不足或请求受限，请检查账户余额与限额"
        else:
            message = f"DeepSeek 返回 {e.response.status_code}: {body}"
        return TestResult(key=key, ok=False, message=message)
    except httpx.RequestError as e:
        return TestResult(key=key, ok=False, message=f"DeepSeek 请求失败: {e}")

    return TestResult(key=key, ok=True, message="DeepSeek 连接正常")


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
