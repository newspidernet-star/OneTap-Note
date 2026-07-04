from datetime import datetime, timezone
import logging
import threading
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import get_settings
from app.database import SessionLocal
from app.models import (
    ApiSettings, EvidenceBlock, Material, Match, Session as SessionModel,
    Summary, Transcript, TranscriptSegment,
)
from app.schemas.summary import (
    KeyPointOut, MatchResponse, SummaryGenerateResponse, SummaryResultOut, VerificationOut,
)
from app.services.matcher import match_evidence
from app.services.summarizer import (
    clear_summary, detect_unused_blocks, generate_summary, save_summary, verify_citations,
)
from app.services.title_generator import generate_title

logger = logging.getLogger("smart_scribe")

router = APIRouter(prefix="/api/summary", tags=["summary"])


def _purge_session(session_id: int) -> None:
    """彻底删除一个会话的 DB 记录 + 媒体文件（用完即焚）。"""
    import shutil
    delay = get_settings().ephemeral_ttl
    def _do():
        time.sleep(delay)
        db = SessionLocal()
        try:
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
            s = db.query(SessionModel).filter_by(id=session_id).first()
            if s:
                db.delete(s)
            db.commit()
        except Exception as e:
            logger.warning("ephemeral purge failed for session %s: %s", session_id, e)
        finally:
            db.close()
        storage_dir = get_settings().storage_dir / f"session_{session_id}"
        if storage_dir.exists():
            try:
                shutil.rmtree(str(storage_dir))
            except Exception as e:
                logger.warning("ephemeral purge rmtree failed: %s", e)
    threading.Thread(target=_do, daemon=True).start()


def _schedule_purge_if_ephemeral(session_id: int) -> None:
    """用完即焚模式：生成完总结后延后删除该会话所有数据。"""
    settings = get_settings()
    if not settings.ephemeral:
        return
    # 若所有 key 都来自环境变量（DB 里无任何 ApiSettings），才自动删除
    has_db_keys = SessionLocal().query(ApiSettings).first() is not None
    if has_db_keys:
        return
    logger.info("[session %s] ephemeral mode: 将在 %ss 后删除", session_id, settings.ephemeral_ttl)
    _purge_session(session_id)


@router.post("/match/{session_id}", response_model=MatchResponse)
def run_match(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        matches = match_evidence(session_id, db)
        session.error_message = None
        db.commit()
        return MatchResponse(pairs_count=len(matches))
    except Exception as e:
        db.rollback()
        session = db.query(SessionModel).filter_by(id=session_id).first()
        if session:
            session.status = "failed"
            session.error_message = str(e)[:500]
            session.updated_at = datetime.now(timezone.utc).isoformat()
            db.commit()
        raise HTTPException(status_code=500, detail="Summary matching failed")


@router.post("/generate/{session_id}", response_model=SummaryGenerateResponse)
def run_generate(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        had_summary = db.query(Summary).filter_by(session_id=session_id).first() is not None
        clear_summary(session_id, db)
        t0 = time.time()
        result = generate_summary(session_id, db)
        logger.info(f"[session {session_id}] DeepSeek 生成完成, 耗时 {time.time()-t0:.2f}s")
        t1 = time.time()
        verification = verify_citations(result, session_id, db)
        result["_citation_valid"] = verification["valid"]
        result["_invalid_citations"] = verification["invalid_ids"]
        save_summary(result, session_id, db)

        # Generate title only on the first successful summary so manual renames are preserved.
        if not had_summary:
            source_text = result.get("summary") or result.get("corrected_text") or ""
            new_title = generate_title(source_text, db)
            if new_title:
                session.title = new_title
        logger.info(f"[session {session_id}] 保存+校验+标题, 耗时 {time.time()-t1:.2f}s")

        session.status = "done"
        session.error_message = None
        session.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        # 用完即焚：在爬取总结结果前不删；返回总结后再删
        _schedule_purge_if_ephemeral(session_id)
        return SummaryGenerateResponse(status="completed")
    except Exception as e:
        db.rollback()
        session = db.query(SessionModel).filter_by(id=session_id).first()
        if session:
            session.status = "failed"
            session.error_message = str(e)[:500]
            session.updated_at = datetime.now(timezone.utc).isoformat()
            db.commit()
        raise HTTPException(status_code=500, detail="Summary generation failed")


@router.get("/result/{session_id}", response_model=SummaryResultOut)
def get_summary_result(session_id: int, db: Session = Depends(get_db)):
    summary = db.query(Summary).filter_by(session_id=session_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="总结结果不存在")
    result_for_verify = {
        "key_points": summary.key_points or [],
        "corrected_text": summary.corrected_text or "",
        "summary": summary.summary_markdown or "",
    }
    v = verify_citations(result_for_verify, session_id, db)
    kps = [KeyPointOut(point=kp["point"], citations=kp.get("citations", [])) for kp in (summary.key_points or [])]
    return SummaryResultOut(
        corrected_text=summary.corrected_text or "",
        summary=summary.summary_markdown or "",
        key_points=kps,
        corrections=[],
        unused_block_ids=summary.unused_block_ids or [],
        citation_valid=v["valid"],
        invalid_citations=v["invalid_ids"],
    )


@router.post("/verify/{session_id}", response_model=VerificationOut)
def re_verify(session_id: int, db: Session = Depends(get_db)):
    summary = db.query(Summary).filter_by(session_id=session_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="总结结果不存在")
    ks = {"key_points": summary.key_points or [], "corrected_text": summary.corrected_text, "summary": summary.summary_markdown}
    v = verify_citations(ks, session_id, db)
    u = detect_unused_blocks(ks, session_id, db)
    return VerificationOut(citation_valid=v["valid"], invalid_citations=v["invalid_ids"], unused_block_ids=u)
