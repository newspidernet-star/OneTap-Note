from datetime import datetime, timezone
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Session as SessionModel, Summary
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
        logger.info(f"🤖 [session {session_id}] DeepSeek 生成完成, 耗时 {time.time()-t0:.2f}s")
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
        logger.info(f"✅ [session {session_id}] 保存+校验+标题, 耗时 {time.time()-t1:.2f}s")

        session.status = "done"
        session.error_message = None
        session.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
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
