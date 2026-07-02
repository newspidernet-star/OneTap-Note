from datetime import datetime, timezone
import asyncio
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, session_factory
from app.models import Material, Session as SessionModel, Transcript, TranscriptSegment
from app.schemas.speech import TranscriptOut, TranscriptionSegmentOut, TranscribeResponse
from app.services.audio_extractor import prepare_audio
from app.services.qwen_asr import transcribe

logger = logging.getLogger("smart_scribe")

router = APIRouter(prefix="/api/speech", tags=["speech"])


def _run_transcribe(audio_path: str, session_id: int) -> list[dict]:
    """Run transcribe in a fresh DB session — safe for thread pools."""
    db = session_factory()
    try:
        return transcribe(audio_path, session_id, db)
    finally:
        db.close()


@router.post("/transcribe/{session_id}", response_model=TranscribeResponse)
async def start_transcribe(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    audio_materials = db.query(Material).filter_by(session_id=session_id, type="audio").all()
    video_materials = db.query(Material).filter_by(session_id=session_id, type="video").all()
    candidates = audio_materials + video_materials
    if not candidates:
        raise HTTPException(status_code=404, detail="会话没有音频或视频素材")
    material = candidates[0]
    session.status = "processing"
    session.error_message = None
    session.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()

    try:
        audio_path = prepare_audio(material)
        t0 = time.time()
        logger.info(f"[session {session_id}] 开始语音转写, 音频={audio_path}")
        await asyncio.to_thread(_run_transcribe, audio_path, session_id)
        logger.info(f"[session {session_id}] 语音转写完成, 耗时 {time.time()-t0:.2f}s")
    except Exception as e:
        msg = str(e)
        if "NO_WORDS" in msg or "ALGO_INVALID_PARAM_AUDIO_FORMAT" in msg or "NO_AUDIO_STREAM" in msg:
            # No speech to transcribe — not a failure, just skip.
            db2 = session_factory()
            try:
                sess = db2.query(SessionModel).filter_by(id=session_id).first()
                if sess:
                    sess.status = "done"
                    sess.error_message = None
                    sess.updated_at = datetime.now(timezone.utc).isoformat()
                    db2.commit()
            finally:
                db2.close()
            return TranscribeResponse(task_id="done", status="completed")
        db2 = session_factory()
        try:
            sess = db2.query(SessionModel).filter_by(id=session_id).first()
            if sess:
                sess.status = "failed"
                sess.error_message = msg[:500]
                sess.updated_at = datetime.now(timezone.utc).isoformat()
                db2.commit()
        finally:
            db2.close()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    db2 = session_factory()
    try:
        sess = db2.query(SessionModel).filter_by(id=session_id).first()
        if sess:
            sess.status = "done"
            sess.error_message = None
            sess.updated_at = datetime.now(timezone.utc).isoformat()
            db2.commit()
    finally:
        db2.close()

    return TranscribeResponse(task_id="done", status="completed")


@router.get("/transcript/{session_id}", response_model=TranscriptOut)
async def get_transcript(session_id: int, db: Session = Depends(get_db)):
    transcript = db.query(Transcript).filter_by(session_id=session_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="转写结果不存在")
    segs = db.query(TranscriptSegment).filter_by(transcript_id=transcript.id).order_by(TranscriptSegment.start_time).all()
    return TranscriptOut(
        session_id=session_id,
        segments=[TranscriptionSegmentOut(start_time=s.start_time, end_time=s.end_time, speaker=s.speaker, text=s.text) for s in segs],
    )
