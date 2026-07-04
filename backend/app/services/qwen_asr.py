import subprocess
import time
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ApiSettings, EvidenceBlock, Transcript, TranscriptSegment
from app.services.crypto import get_secret
from app.services.tunnel import resolve_public_base_url

FUNASR_MODEL = "fun-asr"


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
    resp = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        },
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
    public_base = resolve_public_base_url()
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
    public_url = _public_url_for_local_file(mp3_path)
    if not public_url:
        raise ValueError(
            "语音转写需要公网回拉音频，但未配置 SMART_SCRIBE_PUBLIC_BASE_URL，"
            "且自动隧道未能启动。请设置 SMART_SCRIBE_PUBLIC_BASE_URL 指向本服务公网地址，"
            "或安装 cloudflared 让 SMART_SCRIBE_TUNNEL=auto 自动建立临时隧道。"
        )
    task_id = _submit_funasr(public_url, api_key, workspace_id)
    data = _poll_funasr(task_id, api_key, workspace_id)
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


def transcribe(audio_path: str, session_id: int, db: Session) -> list[dict]:
    api_key, workspace_id = _get_credentials(db)

    mp3_path = _ensure_mp3(audio_path)
    try:
        segments = _transcribe_async(mp3_path, api_key, workspace_id)
    finally:
        if mp3_path != audio_path:
            Path(mp3_path).unlink(missing_ok=True)

    existing = db.query(Transcript).filter_by(session_id=session_id).first()
    if existing:
        db.delete(existing)
        db.flush()

    transcript = Transcript(session_id=session_id)
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

    db.query(EvidenceBlock).filter_by(session_id=session_id, type="speech").delete()
    db.flush()
    for i, seg in enumerate(segments):
        eb = EvidenceBlock(
            block_id=f"S{i + 1:03d}",
            session_id=session_id,
            type="speech",
            timestamp=seg["start_time"],
            end_timestamp=seg["end_time"],
            speaker=seg["speaker"],
            text=seg["text"],
        )
        db.add(eb)

    db.commit()
    return segments
