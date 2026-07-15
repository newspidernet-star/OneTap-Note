import logging
import mimetypes
import re as _re
import subprocess
import time
import uuid
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ApiSettings, EvidenceBlock, Transcript, TranscriptSegment
from app.services.crypto import get_secret
from app.services.tunnel import ensure_public_base_url, reset_tunnel

FUNASR_MODEL = "fun-asr"
logger = logging.getLogger("smart_scribe")


def _is_retriable_public_file_error(error: Exception) -> bool:
    message = str(error)
    normalized = message.upper()
    if "FILE_DOWNLOAD_FAILED" in normalized:
        return True
    return "SERVER_ERROR" in normalized and (
        "TRYCLOUDFLARE" in normalized or "FILE_URL" in normalized
    )


def _max_s_block_number(session_id: int, db: Session) -> int:
    existing = db.query(EvidenceBlock.block_id).filter(
        EvidenceBlock.session_id == session_id,
        EvidenceBlock.block_id.like("S%"),
    ).all()
    max_n = 0
    for (bid,) in existing:
        m = _re.match(r"^S(\d+)$", (bid or "").strip())
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n


def _get_credentials(db: Session) -> tuple[str, str | None]:
    key = get_secret(db, "dashscope_api_key")
    if not key:
        raise ValueError("DashScope API key 未配置（设置页或 SMART_SCRIBE_DASHSCOPE_API_KEY 环境变量）")
    workspace = get_secret(db, "dashscope_workspace_id")
    return key, workspace


def _base_url(workspace_id: str | None) -> str:
    if workspace_id:
        return f"https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1"
    return "https://dashscope.aliyuncs.com/api/v1"


def _ensure_mp3(path: str) -> str:
    """Produce a 16kHz mono 32kbps MP3 with a safe ASCII filename next to the input."""
    p = Path(path)
    out = p.parent / "_asr_tmp.mp3"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(p),
                "-ar", "16000", "-ac", "1", "-b:a", "32k",
                "-c:a", "libmp3lame",
                str(out),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception:
        out.unlink(missing_ok=True)
        raise
    return str(out)


def _submit_funasr(file_url: str, api_key: str, workspace_id: str | None) -> str:
    url = f"{_base_url(workspace_id)}/services/audio/asr/transcription"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    if file_url.startswith("oss://"):
        headers["X-DashScope-OssResourceResolve"] = "enable"
    resp = httpx.post(
        url,
        headers=headers,
        json={
            "model": FUNASR_MODEL,
            "input": {"file_urls": [file_url]},
            "parameters": {
                "channel_id": [0],
                "language_hints": ["zh"],
                "diarization_enabled": True,
            },
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    task_id = data.get("output", {}).get("task_id")
    if not task_id:
        raise ValueError(f"提交 Fun‑ASR 任务失败: {data}")
    return task_id


def _upload_to_dashscope_temp(file_path: str, api_key: str) -> str:
    """Upload one ASR input to DashScope's private 48-hour temporary storage."""
    path = Path(file_path)
    policy_response = httpx.get(
        "https://dashscope.aliyuncs.com/api/v1/uploads",
        params={"action": "getPolicy", "model": FUNASR_MODEL},
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    policy_response.raise_for_status()
    policy = policy_response.json().get("data", {})
    required = (
        "policy",
        "signature",
        "upload_dir",
        "upload_host",
        "oss_access_key_id",
        "x_oss_object_acl",
        "x_oss_forbid_overwrite",
    )
    missing = [field for field in required if not policy.get(field)]
    if missing:
        raise ValueError(f"DashScope upload policy is missing: {', '.join(missing)}")

    max_size_mb = float(policy.get("max_file_size_mb") or 0)
    if max_size_mb and path.stat().st_size > max_size_mb * 1024 * 1024:
        raise ValueError(f"ASR audio exceeds DashScope temporary upload limit ({max_size_mb:g} MB)")

    suffix = path.suffix.lower() or ".mp3"
    upload_name = f"onetap-asr-{uuid.uuid4().hex}{suffix}"
    object_key = f"{policy['upload_dir'].rstrip('/')}/{upload_name}"
    content_type = mimetypes.guess_type(upload_name)[0] or "application/octet-stream"
    with path.open("rb") as handle:
        upload_response = httpx.post(
            policy["upload_host"],
            files=[
                ("OSSAccessKeyId", (None, policy["oss_access_key_id"])),
                ("policy", (None, policy["policy"])),
                ("Signature", (None, policy["signature"])),
                ("key", (None, object_key)),
                ("x-oss-object-acl", (None, policy["x_oss_object_acl"])),
                ("x-oss-forbid-overwrite", (None, policy["x_oss_forbid_overwrite"])),
                ("success_action_status", (None, "200")),
                ("file", (upload_name, handle, content_type)),
            ],
            timeout=120,
        )
    upload_response.raise_for_status()
    return f"oss://{object_key}"


def _poll_funasr(task_id: str, api_key: str, workspace_id: str | None, max_attempts: int = 600) -> dict:
    url = f"{_base_url(workspace_id)}/tasks/{task_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    for _ in range(max_attempts):
        resp = httpx.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("output", {}).get("task_status", "").upper()
        if status == "SUCCEEDED":
            return data
        if status in ("FAILED", "UNKNOWN"):
            raise ValueError(f"ASR 任务失败: {data}")
        time.sleep(1)
    raise TimeoutError("ASR 任务轮询超时")


def _download_funasr(data: dict) -> dict:
    results = data.get("output", {}).get("results", [])
    if not results:
        raise ValueError("ASR 结果为空")
    first = results[0]
    if first.get("subtask_status") != "SUCCEEDED":
        raise ValueError(f"子任务失败: {first}")
    result_url = first.get("transcription_url")
    if not result_url:
        raise ValueError("ASR 结果 URL 为空")
    resp = httpx.get(result_url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _parse_filetrans_response(result: dict) -> list[dict]:
    segments = []
    for transcript in result.get("transcripts", []):
        speaker = transcript.get("speaker") or transcript.get("speaker_id")
        if speaker is not None:
            speaker = str(speaker)
        else:
            speaker = "未知"
        for sentence in transcript.get("sentences", []):
            seg_speaker = sentence.get("speaker_id")
            segments.append({
                "start_time": float(sentence.get("begin_time", 0)) / 1000,
                "end_time": float(sentence.get("end_time", 0)) / 1000,
                "speaker": str(seg_speaker) if seg_speaker is not None else speaker,
                "text": sentence.get("text", ""),
            })
    if not segments:
        for transcript in result.get("transcripts", []):
            speaker = transcript.get("speaker") or transcript.get("speaker_id")
            segments.append({
                "start_time": 0.0,
                "end_time": 0.0,
                "speaker": str(speaker) if speaker is not None else "未知",
                "text": transcript.get("text", ""),
            })
    return segments


def _public_url_for_local_file(audio_path: str) -> str | None:
    public_base = ensure_public_base_url()
    if not public_base:
        return None
    sdir = get_settings().storage_dir.resolve()
    p = Path(audio_path).resolve()
    try:
        rel = p.relative_to(sdir)
    except ValueError:
        return None
    return f"{public_base}/static/media/{rel.as_posix()}"


def _transcribe_async(mp3_path: str, api_key: str, workspace_id: str | None) -> list[dict]:
    using_dashscope_storage = True
    try:
        public_url = _upload_to_dashscope_temp(mp3_path, api_key)
        logger.info("ASR input uploaded to DashScope temporary storage")
    except Exception as upload_error:
        using_dashscope_storage = False
        logger.warning(
            "DashScope temporary upload unavailable; falling back to public tunnel: %s",
            upload_error,
        )
        public_url = _public_url_for_local_file(mp3_path)
        if not public_url:
            raise ValueError(
                "Unable to deliver audio to the transcription service through temporary storage or a public tunnel"
            ) from upload_error

    # Retry delivery failures with a fresh temporary object or a rebuilt tunnel.
    max_attempts = 3
    last_err = None
    for attempt in range(max_attempts):
        try:
            task_id = _submit_funasr(public_url, api_key, workspace_id)
            data = _poll_funasr(task_id, api_key, workspace_id)
            break
        except ValueError as e:
            last_err = e
            if _is_retriable_public_file_error(e) and attempt < max_attempts - 1:
                if using_dashscope_storage:
                    logger.warning(
                        "ASR temporary file fetch failed (attempt %d/%d), uploading a fresh copy...",
                        attempt + 1,
                        max_attempts,
                    )
                    public_url = _upload_to_dashscope_temp(mp3_path, api_key)
                else:
                    logger.warning(
                        "ASR public file fetch failed (attempt %d/%d), rebuilding tunnel and retrying...",
                        attempt + 1,
                        max_attempts,
                    )
                    if not get_settings().public_base_url:
                        reset_tunnel()
                        public_url = _public_url_for_local_file(mp3_path)
                time.sleep(2)
                continue
            raise
    else:
        raise last_err
    result = _download_funasr(data)
    segments = _parse_filetrans_response(result)
    # Map numeric speaker_id → "说话人1", "说话人2", …
    speakers: dict[str, str] = {}
    for seg in segments:
        sid = seg["speaker"]
        if sid != "未知" and sid not in speakers:
            speakers[sid] = f"说话人{len(speakers) + 1}"
    for seg in segments:
        if seg["speaker"] in speakers:
            seg["speaker"] = speakers[seg["speaker"]]
    return segments


def transcribe(audio_path: str, session_id: int, db: Session, material_id: int | None = None) -> list[dict]:
    api_key, workspace_id = _get_credentials(db)

    mp3_path = _ensure_mp3(audio_path)
    try:
        segments = _transcribe_async(mp3_path, api_key, workspace_id)
    finally:
        if mp3_path != audio_path:
            Path(mp3_path).unlink(missing_ok=True)

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

    if material_id is not None:
        db.query(EvidenceBlock).filter_by(session_id=session_id, type="speech", material_id=material_id).delete()
    else:
        db.query(EvidenceBlock).filter_by(session_id=session_id, type="speech").delete()
    db.flush()
    next_s = _max_s_block_number(session_id, db) + 1
    for seg in segments:
        eb = EvidenceBlock(
            block_id=f"S{next_s:03d}",
            session_id=session_id,
            material_id=material_id,
            type="speech",
            timestamp=seg["start_time"],
            end_timestamp=seg["end_time"],
            speaker=seg["speaker"],
            text=seg["text"],
        )
        db.add(eb)
        next_s += 1

    db.commit()
    return segments
