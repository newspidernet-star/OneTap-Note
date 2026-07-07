from datetime import datetime, timezone
import asyncio
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, session_factory
from app.models import Material, Session as SessionModel, Transcript, TranscriptSegment
from app.schemas.speech import TranscriptOut, TranscribeResponse, TranscriptionSegmentOut
from app.services.audio_extractor import prepare_audio
from app.services.qwen_asr import transcribe
from app.services.progress import fail_progress, finish_progress, set_progress

logger = logging.getLogger("smart_scribe")

router = APIRouter(prefix="/api/speech", tags=["speech"])


def _run_transcribe(audio_path: str, session_id: int, material_id: int | None = None) -> list[dict]:
    db = session_factory()
    try:
        return transcribe(audio_path, session_id, db, material_id=material_id)
    finally:
        db.close()


@router.post("/transcribe/{session_id}", response_model=TranscribeResponse)
async def start_transcribe(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    audio_materials = db.query(Material).filter_by(session_id=session_id, type="audio").order_by(Material.sort_order).all()
    video_materials = db.query(Material).filter_by(session_id=session_id, type="video").order_by(Material.sort_order).all()
    candidates = audio_materials + video_materials
    if not candidates:
        raise HTTPException(status_code=404, detail="会话没有音频或视频素材")

    session.status = "processing"
    session.error_message = None
    session.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()

    for material_index, material in enumerate(candidates, start=1):
        try:
            set_progress(
                session_id,
                "transcribe",
                "正在识别语音内容",
                f"第 {material_index}/{len(candidates)} 个音视频素材",
            )
            material.status = "transcribing"
            db.commit()
            audio_path = prepare_audio(material)
            t0 = time.time()
            logger.info("[ASR] session %s: transcribe material %s, audio=%s", session_id, material.id, audio_path)
            await asyncio.to_thread(_run_transcribe, audio_path, session_id, material.id)
            logger.info("[OK] session %s: material %s done, %.2fs", session_id, material.id, time.time() - t0)
            db2 = session_factory()
            try:
                mat = db2.query(Material).filter_by(id=material.id, session_id=session_id).first()
                if mat:
                    mat.status = "done"
                    db2.commit()
            finally:
                db2.close()
        except Exception as e:
            msg = str(e)
            if "NO_WORDS" in msg or "ALGO_INVALID_PARAM_AUDIO_FORMAT" in msg or "NO_AUDIO_STREAM" in msg:
                logger.info("[ASR] session %s: material %s has no speech, skipping", session_id, material.id)
                db2 = session_factory()
                try:
                    mat = db2.query(Material).filter_by(id=material.id, session_id=session_id).first()
                    if mat:
                        mat.status = "no_speech"
                        db2.commit()
                finally:
                    db2.close()
                continue
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
            fail_progress(session_id, msg)
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

    finish_progress(session_id, "语音转写完成", "可以生成知识笔记")

    return TranscribeResponse(task_id="done", status="completed")


@router.get("/transcript/{session_id}", response_model=TranscriptOut)
async def get_transcript(session_id: int, db: Session = Depends(get_db)):
    transcripts = db.query(Transcript).filter_by(session_id=session_id).all()
    if not transcripts:
        raise HTTPException(status_code=404, detail="转写结果不存在")

    material_order = {
        m.id: m.sort_order
        for m in db.query(Material).filter_by(session_id=session_id).all()
    }
    ordered: list[tuple[int, float, TranscriptionSegmentOut]] = []
    for transcript in transcripts:
        segs = db.query(TranscriptSegment).filter_by(transcript_id=transcript.id).order_by(TranscriptSegment.start_time).all()
        order = material_order.get(transcript.material_id, 0)
        for seg in segs:
            ordered.append((
                order,
                seg.start_time,
                TranscriptionSegmentOut(
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    speaker=seg.speaker,
                    text=seg.text,
                ),
            ))
    ordered.sort(key=lambda item: (item[0], item[1]))
    return TranscriptOut(session_id=session_id, segments=[item[2] for item in ordered])
