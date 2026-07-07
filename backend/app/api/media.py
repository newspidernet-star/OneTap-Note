import logging
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import get_settings
from app.models import ApiSettings, EvidenceBlock, Material, Match, Summary, Session as SessionModel, Transcript, TranscriptSegment
from app.schemas.media import MaterialOut, SessionCreate, SessionOut, UploadResponse
from app.services.crypto import get_secret
from app.services.frame_extractor import extract_frame_at
from app.services.ocr import ocr_batch, ocr_image
from app.services.pipeline import process_session
from app.services.progress import clear_progress, fail_progress, finish_progress, get_progress, set_progress
from app.services.downloader import download
from app.services.storage import classify_media, resolve_storage_path, save_upload, session_storage_dir

logger = logging.getLogger("smart_scribe")

router = APIRouter(tags=["media"])


def _storage_url(file_path: str | None) -> str | None:
    if not file_path:
        return None
    sdir = get_settings().storage_dir.resolve()
    p = Path(resolve_storage_path(file_path))
    try:
        rel = p.resolve().relative_to(sdir)
    except ValueError:
        try:
            rel = Path(file_path).relative_to(get_settings().storage_dir)
        except ValueError:
            return None
    return f"/static/media/{rel.as_posix()}"


def _next_p_block_id(session_id: int, db: Session) -> str:
    existing = db.query(EvidenceBlock.block_id).filter(
        EvidenceBlock.session_id == session_id,
        EvidenceBlock.block_id.like("P%"),
    ).all()
    max_n = 0
    for (bid,) in existing:
        m = re.match(r"^P(\d+)$", (bid or "").strip())
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"P{max_n + 1:03d}"


def _clear_stale_summary_and_matches(session_id: int, db: Session) -> None:
    db.query(Summary).filter(Summary.session_id == session_id).delete(synchronize_session=False)
    valid_ids = [row[0] for row in db.query(EvidenceBlock.id).filter_by(session_id=session_id).all()]
    if valid_ids:
        db.query(Match).filter(
            (~Match.speech_block_id.in_(valid_ids)) | (~Match.screen_block_id.in_(valid_ids))
        ).delete(synchronize_session=False)
    else:
        db.query(Match).delete(synchronize_session=False)


def _has_pending_transcription(session_id: int, db: Session) -> bool:
    speech_material_ids = {
        row[0]
        for row in db.query(EvidenceBlock.material_id).filter(
            EvidenceBlock.session_id == session_id,
            EvidenceBlock.type == "speech",
            EvidenceBlock.material_id.isnot(None),
        ).distinct()
    }
    materials = db.query(Material).filter(
        Material.session_id == session_id,
        Material.type.in_(["audio", "video"]),
    ).all()
    return any(
        m.status != "no_speech" and m.id not in speech_material_ids
        for m in materials
    )


@router.get("/api/sessions", response_model=list[SessionOut])
def list_sessions(client_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(SessionModel)
    # 仅在 ephemeral 模式下按 client_id 隔离（共享部署）；本地默认无隔离，自己能看到全部会话
    if client_id and get_settings().ephemeral:
        q = q.filter(SessionModel.client_id == client_id)
    return q.order_by(SessionModel.created_at.desc()).all()


@router.post("/api/sessions", response_model=SessionOut)
async def create_session(body: SessionCreate, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).isoformat()
    latest_id = db.query(func.max(SessionModel.id)).scalar() or 0
    next_id = max(int(time.time() * 1000), latest_id + 1)
    s = SessionModel(
        id=next_id,
        title=body.title,
        status="created",
        created_at=now,
        updated_at=now,
        client_id=body.client_id,
        last_seen_at=now,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    clear_progress(s.id)
    return s


@router.post("/api/sessions/{session_id}/heartbeat")
def heartbeat(session_id: int, body: dict | None = None, db: Session = Depends(get_db)):
    """前端每 15s 调一次，续命 last_seen_at。后台清扫线程据此判断是否离线。"""
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # 可选：允许在 body 里校验 client_id 归属
    if body and body.get("client_id") and session.client_id and session.client_id != body["client_id"]:
        raise HTTPException(status_code=403, detail="Session belongs to another client")
    session.last_seen_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"ok": True, "last_seen_at": session.last_seen_at}


@router.get("/api/sessions/{session_id}/progress")
def processing_progress(session_id: int, db: Session = Depends(get_db)):
    if not db.query(SessionModel.id).filter_by(id=session_id).first():
        raise HTTPException(status_code=404, detail="Session not found")
    return get_progress(session_id)


@router.post("/api/media/upload", response_model=UploadResponse)
async def upload_file(
    session_id: int = Form(...),
    sort_order: int = Form(0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    set_progress(session_id, "upload", "正在接收本地素材", file.filename or "")
    media_type = classify_media(file.filename, file.content_type)
    file_path = save_upload(file, session_id)
    m = Material(
        session_id=session_id,
        type=media_type,
        source="local_file",
        file_path=file_path,
        sort_order=sort_order,
        status="pending",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return UploadResponse(material_id=m.id, type=media_type, status="pending")


@router.get("/api/media/session/{session_id}/materials", response_model=list[MaterialOut])
async def list_materials(session_id: int, db: Session = Depends(get_db)):
    materials = db.query(Material).filter_by(session_id=session_id).order_by(Material.sort_order).all()
    return [
        MaterialOut(
            id=m.id,
            type=m.type,
            source=m.source,
            sort_order=m.sort_order,
            status=m.status,
            url=_storage_url(m.file_path),
        )
        for m in materials
    ]


@router.post("/api/media/session/{session_id}/process")
def process_materials(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        set_progress(
            session_id,
            "prepare",
            "正在准备素材",
            "视频使用快速语音模式；图片与手动选帧仍会识别文字",
        )
        pre_block_ids = {b.id for b in db.query(EvidenceBlock).filter_by(session_id=session_id).all()}
        t0 = time.time()
        result = process_session(session_id, db)
        current_block_ids = {b.id for b in db.query(EvidenceBlock).filter_by(session_id=session_id).all()}
        if result.evidence_block_ids or (current_block_ids - pre_block_ids):
            _clear_stale_summary_and_matches(session_id, db)
        logger.info(f"[session {session_id}] process 总耗时 {time.time()-t0:.2f}s")
        session.status = "processing" if _has_pending_transcription(session_id, db) else "done"
        session.error_message = None
        session.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        if not _has_pending_transcription(session_id, db):
            finish_progress(session_id, "素材已就绪", "可以生成知识笔记")
        return {
            "frames_count": result.frames_count,
            "ocr_pages_count": result.ocr_pages_count,
            "evidence_block_ids": result.evidence_block_ids,
        }
    except Exception as e:
        fail_progress(session_id, str(e))
        db.rollback()
        session = db.query(SessionModel).filter_by(id=session_id).first()
        if session:
            session.status = "failed"
            session.error_message = str(e)[:500]
            session.updated_at = datetime.now(timezone.utc).isoformat()
            db.commit()
        raise HTTPException(status_code=500, detail="Processing failed")


@router.delete("/api/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    return _delete_session_impl(session_id, db)


@router.post("/api/sessions/{session_id}/purge")
def purge_session_via_post(session_id: int, db: Session = Depends(get_db)):
    """sendBeacon 只能发 POST，关标签时用它触发删除（等同 DELETE）。"""
    return _delete_session_impl(session_id, db)


def _delete_session_impl(session_id: int, db: Session) -> dict:
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.query(Match).filter(
        Match.speech_block_id.in_(
            db.query(EvidenceBlock.id).filter(EvidenceBlock.session_id == session_id)
        )
    ).delete(synchronize_session=False)

    db.query(TranscriptSegment).filter(
        TranscriptSegment.transcript_id.in_(
            db.query(Transcript.id).filter(Transcript.session_id == session_id)
        )
    ).delete(synchronize_session=False)

    db.query(Transcript).filter(Transcript.session_id == session_id).delete(synchronize_session=False)
    db.query(EvidenceBlock).filter(EvidenceBlock.session_id == session_id).delete(synchronize_session=False)
    db.query(Material).filter(Material.session_id == session_id).delete(synchronize_session=False)
    db.query(Summary).filter(Summary.session_id == session_id).delete(synchronize_session=False)
    db.delete(session)
    db.commit()
    clear_progress(session_id)

    storage_dir = get_settings().storage_dir / f"session_{session_id}"
    if storage_dir.exists():
        for attempt in range(3):
            try:
                shutil.rmtree(str(storage_dir))
                break
            except OSError as e:
                if attempt == 2:
                    logger.warning("delete_session rmtree failed for session %s: %s", session_id, e)
                else:
                    time.sleep(0.2 * (attempt + 1))

    return {"ok": True}


@router.patch("/api/sessions/{session_id}")
def update_session(session_id: int, body: SessionCreate, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.title = body.title[:200]
    session.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"id": session.id, "title": session.title, "status": session.status, "created_at": session.created_at, "updated_at": session.updated_at, "error_message": session.error_message}


@router.get("/api/media/evidence/{session_id}")
def list_evidence(session_id: int, db: Session = Depends(get_db)):
    blocks = db.query(EvidenceBlock).filter_by(session_id=session_id).order_by(EvidenceBlock.timestamp).all()
    return [
        {
            "id": b.block_id,
            "type": b.type,
            "timestamp": b.timestamp,
            "end_timestamp": b.end_timestamp,
            "speaker": b.speaker,
            "text": b.text,
            "page_number": b.page_number,
            "material_id": b.material_id,
            "image_url": _storage_url(b.image_path),
            "is_manual": bool(b.is_manual),
        }
        for b in blocks
    ]


@router.post("/api/media/session/{session_id}/frame")
def capture_frame(session_id: int, body: dict, db: Session = Depends(get_db)):
    material_id = body.get("material_id")
    timestamp = body.get("timestamp")
    if material_id is None or timestamp is None:
        raise HTTPException(status_code=400, detail="material_id and timestamp are required")
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    material = db.query(Material).filter_by(id=material_id, session_id=session_id).first()
    if not material or material.type != "video":
        raise HTTPException(status_code=404, detail="Video material not found")

    ts = max(0.0, float(timestamp))
    frames_dir = session_storage_dir(session_id) / "frames"
    frame_path = extract_frame_at(
        resolve_storage_path(material.file_path),
        ts,
        str(frames_dir),
        f"manual_{int(ts * 1000)}.jpg",
    )
    if not frame_path:
        raise HTTPException(status_code=500, detail="Frame capture failed")

    result = ocr_image(frame_path, db)
    block_id = _next_p_block_id(session_id, db)
    block = EvidenceBlock(
        block_id=block_id,
        session_id=session_id,
        material_id=material.id,
        type="video_frame",
        timestamp=ts,
        text=result.text,
        image_path=frame_path,
        is_manual=True,
    )
    db.add(block)
    _clear_stale_summary_and_matches(session_id, db)
    db.commit()
    db.refresh(block)
    return {
        "id": block.block_id,
        "type": block.type,
        "timestamp": block.timestamp,
        "text": block.text,
        "material_id": block.material_id,
        "image_url": _storage_url(block.image_path),
        "is_manual": bool(block.is_manual),
    }


@router.post("/api/media/session/{session_id}/frames")
def capture_frames_batch(session_id: int, body: dict, db: Session = Depends(get_db)):
    material_id = body.get("material_id")
    timestamps = body.get("timestamps")
    if material_id is None or not isinstance(timestamps, list):
        raise HTTPException(status_code=400, detail="material_id and timestamps[] are required")
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    material = db.query(Material).filter_by(id=material_id, session_id=session_id).first()
    if not material or material.type != "video":
        raise HTTPException(status_code=404, detail="Video material not found")

    unique_ts = sorted({int(max(0.0, float(ts)) * 1000): max(0.0, float(ts)) for ts in timestamps}.items())
    unique_ts = unique_ts[:50]
    frames_dir = session_storage_dir(session_id) / "frames"
    frame_items: list[tuple[float, str]] = []
    skipped: list[float] = []
    for key, ts in unique_ts:
        frame_path = extract_frame_at(
            resolve_storage_path(material.file_path),
            ts,
            str(frames_dir),
            f"manual_{key}.jpg",
        )
        if frame_path:
            frame_items.append((ts, frame_path))
        else:
            skipped.append(ts)

    results = ocr_batch([path for _, path in frame_items], db) if frame_items else []
    blocks = []
    for idx, (ts, frame_path) in enumerate(frame_items):
        text = results[idx].text if idx < len(results) else ""
        block_id = _next_p_block_id(session_id, db)
        block = EvidenceBlock(
            block_id=block_id,
            session_id=session_id,
            material_id=material.id,
            type="video_frame",
            timestamp=ts,
            text=text,
            image_path=frame_path,
            is_manual=True,
        )
        db.add(block)
        db.flush()
        blocks.append({
            "id": block.block_id,
            "type": block.type,
            "timestamp": block.timestamp,
            "text": block.text,
            "material_id": block.material_id,
            "image_url": _storage_url(block.image_path),
            "is_manual": bool(block.is_manual),
        })
    if blocks:
        _clear_stale_summary_and_matches(session_id, db)
    db.commit()
    return {"blocks": blocks, "skipped": skipped}


_log = logging.getLogger("smart_scribe")


@router.post("/api/media/download/{session_id}")
def download_link(session_id: int, body: dict, db: Session = Depends(get_db)):
    url = body.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL required")
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    set_progress(session_id, "download", "正在下载链接素材", url)

    # 防重复：如果同一 URL 已经在这个会话里下载过，跳过
    from app.services.downloader import _extract_url
    clean_url = _extract_url(url)
    existing = db.query(Material).filter_by(session_id=session_id, original_url=clean_url).first()
    if existing:
        logger.info(f"[DL] session {session_id}: URL already downloaded (material {existing.id}), skipping")
        finish_progress(session_id, "链接素材已存在", "已跳过重复下载")
        return {"materials": [MaterialOut(
            id=existing.id, type=existing.type, source=existing.source,
            status=existing.status, sort_order=existing.sort_order,
            url=_storage_url(existing.file_path),
        )]}

    cookie_path = get_secret(db, "ytdlp_cookie_path")

    # 确保会话存储目录存在（可能被之前的 delete_session 清掉了）
    session_storage_dir(session_id)
    try:
        t0 = time.time()
        specs = download(url, session_id, cookie_path=cookie_path)
        logger.info(f"[DL] session {session_id}: downloaded {len(specs)} files, {time.time()-t0:.2f}s")
    except Exception as e:
        fail_progress(session_id, str(e))
        _log.warning("Download failed for %s: %s", url, e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"下载失败: {e}")
    existing_count = db.query(Material).filter_by(session_id=session_id).count()
    results = []
    for spec in specs:
        mat = Material(
            session_id=session_id,
            type=spec.media_type,
            source="download",
            file_path=str(spec.file_path),
            original_url=spec.original_url,
            status="pending",
            sort_order=existing_count + len(results),
        )
        db.add(mat)
        db.flush()
        results.append(MaterialOut(
            id=mat.id, type=mat.type, source=mat.source,
            status=mat.status, sort_order=mat.sort_order,
            url=_storage_url(mat.file_path),
        ))
    session.status = "processing"
    session.error_message = None
    session.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"materials": results}
