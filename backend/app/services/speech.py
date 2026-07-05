import time
import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ApiSettings, Transcript, TranscriptSegment
from app.services.crypto import decrypt

VOLCANO_ASR_URL = "https://openspeech.bytedance.com/api/v3/asr"


def _get_volcano_credentials(db: Session) -> tuple[str, str]:
    app_id = db.query(ApiSettings).filter_by(key="volcano_app_id").first()
    token = db.query(ApiSettings).filter_by(key="volcano_access_token").first()
    if not app_id or not token:
        raise ValueError("火山引擎语音 API 未配置")
    return decrypt(app_id.encrypted_value), decrypt(token.encrypted_value)


def _submit_asr_task(audio_path: str, app_id: str, token: str) -> str:
    with open(audio_path, "rb") as f:
        resp = httpx.post(
            f"{VOLCANO_ASR_URL}/submit",
            headers={
                "Authorization": f"Bearer {token}",
                "X-App-Id": app_id,
            },
            files={"audio": f},
            timeout=30,
        )
    resp.raise_for_status()
    data = resp.json()
    return data["task_id"]


def _poll_asr_result(task_id: str, app_id: str, token: str) -> dict:
    for _ in range(120):
        resp = httpx.post(
            f"{VOLCANO_ASR_URL}/query",
            headers={
                "Authorization": f"Bearer {token}",
                "X-App-Id": app_id,
            },
            json={"task_id": task_id},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "completed":
            return data
        time.sleep(2)
    raise TimeoutError("语音转写超时")


def _parse_segments(raw: dict) -> list[dict]:
    segments = []
    for seg in raw.get("utterances", raw.get("segments", [])):
        segments.append({
            "start_time": float(seg.get("start_time", 0)) / 1000,
            "end_time": float(seg.get("end_time", 0)) / 1000,
            "speaker": str(seg.get("speaker", "未知")),
            "text": seg.get("text", ""),
        })
    return segments


def transcribe(audio_path: str, session_id: int, db: Session, material_id: int | None = None) -> list[dict]:
    app_id, token = _get_volcano_credentials(db)
    task_id = _submit_asr_task(audio_path, app_id, token)
    raw = _poll_asr_result(task_id, app_id, token)
    segments = _parse_segments(raw)

    existing = db.query(Transcript).filter_by(session_id=session_id, material_id=material_id).first()
    if existing:
        db.delete(existing)
        db.flush()

    transcript = Transcript(session_id=session_id, material_id=material_id)
    db.add(transcript)
    db.flush()

    for seg in segments:
        ts = TranscriptSegment(
            transcript_id=transcript.id,
            start_time=seg["start_time"],
            end_time=seg["end_time"],
            speaker=seg["speaker"],
            text=seg["text"],
        )
        db.add(ts)
    db.commit()
    return segments
