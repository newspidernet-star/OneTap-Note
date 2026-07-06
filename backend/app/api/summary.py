from datetime import datetime, timezone
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import EvidenceBlock, Material, Session as SessionModel, Summary
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


def _pending_transcription_material_ids(session_id: int, db: Session) -> list[int]:
    speech_material_ids = {
        row[0]
        for row in db.query(EvidenceBlock.material_id).filter(
            EvidenceBlock.session_id == session_id,
            EvidenceBlock.type == "speech",
            EvidenceBlock.material_id.isnot(None),
        ).distinct()
    }
    has_legacy_speech = db.query(EvidenceBlock.id).filter(
        EvidenceBlock.session_id == session_id,
        EvidenceBlock.type == "speech",
        EvidenceBlock.material_id.is_(None),
    ).first() is not None
    materials = db.query(Material).filter(
        Material.session_id == session_id,
        Material.type.in_(["audio", "video"]),
    ).order_by(Material.sort_order).all()
    pending: list[int] = []
    for material in materials:
        if material.status == "no_speech":
            continue
        if material.id in speech_material_ids:
            continue
        if has_legacy_speech and len(materials) == 1:
            continue
        pending.append(material.id)
    return pending


def _ensure_transcription_ready(session_id: int, db: Session) -> None:
    pending = _pending_transcription_material_ids(session_id, db)
    if pending:
        raise HTTPException(
            status_code=409,
            detail="语音转写还没有完成，请等音频/视频转写完成后再生成总结。",
        )


@router.post("/match/{session_id}", response_model=MatchResponse)
def run_match(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _ensure_transcription_ready(session_id, db)
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
    _ensure_transcription_ready(session_id, db)
    try:
        had_summary = db.query(Summary).filter_by(session_id=session_id).first() is not None
        clear_summary(session_id, db)
        t0 = time.time()
        result = generate_summary(session_id, db)
        logger.info(f"[AI] session {session_id}: DeepSeek done, {time.time()-t0:.2f}s")
        t1 = time.time()
        verification = verify_citations(result, session_id, db)
        result["_citation_valid"] = verification["valid"]
        result["_invalid_citations"] = verification["invalid_ids"]
        save_summary(result, session_id, db)

        # Generate title only on the first successful summary so manual renames are preserved.
        # 优先用 OCR 文字（画面上的准确），ASR 兜底（ASR 可能把"大江大河"转成"大寻劝"）
        if not had_summary:
            ocr_texts = db.query(EvidenceBlock).filter(
                EvidenceBlock.session_id == session_id,
                EvidenceBlock.type.in_(["image", "video_frame"]),
            ).order_by(EvidenceBlock.timestamp).all()
            ocr_text = " ".join(b.text for b in ocr_texts if b.text)[:1500]
            asr_text = (result.get("corrected_text") or result.get("summary") or "")[:1500]
            # OCR 优先（画面文字准确，如项目名"大江大河"），OCR 为空才用 ASR
            source_text = ocr_text if ocr_text and len(ocr_text) > 10 else asr_text
            logger.info(f"[TITLE] session {session_id}: OCR text len={len(ocr_text)}, ASR text len={len(asr_text)}, using {'OCR' if ocr_text and len(ocr_text) > 10 else 'ASR'}")
            new_title = generate_title(source_text, db)
            if new_title:
                session.title = new_title
        logger.info(f"[OK] session {session_id}: saved+verified+title, {time.time()-t1:.2f}s")

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


def _fmt_ts(seconds: float | int | None) -> str:
    if seconds is None:
        return "00:00"
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


def _yaml_string(value: str) -> str:
    escaped = (value or "").replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _compact_ids(ids: list[str]) -> str:
    return " ".join(f"`{cid}`" for cid in ids if cid)


def _clip(text: str, limit: int = 52) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _block_heading(block: EvidenceBlock) -> str:
    ts_str = _fmt_ts(block.timestamp)
    if block.type == "speech":
        who = block.speaker or "说话人"
        return f"{block.block_id} · {ts_str} · {who}"
    if block.type in ("video_frame", "image"):
        page = f"第 {block.page_number} 页" if block.page_number else "画面"
        return f"{block.block_id} · {ts_str} · {page}"
    return f"{block.block_id} · {ts_str}"


@router.get("/export/{session_id}")
def export_obsidian_md(session_id: int, db: Session = Depends(get_db)):
    """导出为 Obsidian 兼容的 Markdown 文档。"""
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    summary = db.query(Summary).filter_by(session_id=session_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="总结结果不存在")

    blocks = db.query(EvidenceBlock).filter_by(session_id=session_id).order_by(EvidenceBlock.timestamp).all()
    title = session.title or "Untitled"
    created = session.created_at[:10] if session.created_at else ""
    unused_ids = summary.unused_block_ids or []
    key_points = summary.key_points or []

    lines: list[str] = []
    # --- Frontmatter ---
    lines.append("---")
    lines.append(f"title: {_yaml_string(title)}")
    if created:
        lines.append(f"date: {created}")
    lines.append("source: smart-scribe")
    lines.append("status: 待整理")
    lines.append(f"evidence_count: {len(blocks)}")
    lines.append("tags:")
    lines.append("  - smart-scribe")
    lines.append("  - 待整理")
    lines.append("---")
    lines.append("")

    # --- 标题 ---
    lines.append(f"# {title}")
    lines.append("")

    # --- 元信息 callout ---
    lines.append("> [!info] 来源")
    lines.append(f"> Smart Scribe 自动整理。创建时间：{session.created_at or '未知'}")
    lines.append(f"> 证据块：{len(blocks)} 个；未被引用：{len(unused_ids)} 个。")
    lines.append("")

    if summary.summary_markdown:
        lines.append("## 核心洞见")
        lines.append("")
        lines.append(summary.summary_markdown.strip())
        lines.append("")

    # --- 核心要点 ---
    if key_points:
        lines.append("## 关键要点")
        lines.append("")
        for kp in key_points:
            point = kp.get("point", "")
            citations = kp.get("citations", [])
            if citations:
                lines.append(f"- {point}")
                lines.append(f"  - 证据：{_compact_ids([str(cid) for cid in citations])}")
            else:
                lines.append(f"- {point}")
        lines.append("")

    if key_points:
        lines.append("## 复习线索")
        lines.append("")
        for kp in key_points[:3]:
            point = _clip(kp.get("point", ""))
            if point:
                lines.append(f"- 我能否用自己的话解释：{point}")
        lines.append("- 哪些结论需要回到详细原文核对？")
        lines.append("")

    if unused_ids:
        lines.append("## 质检提示")
        lines.append("")
        lines.append(f"- 有 {len(unused_ids)} 个证据块没有被 AI 摘要或要点引用，可能是噪声、重复内容，也可能是遗漏信息。")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>查看未引用证据 ID</summary>")
        lines.append("")
        lines.append(_compact_ids(unused_ids))
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # --- 详细原文 ---
    if blocks:
        lines.append("## 详细原文")
        lines.append("")
        lines.append("<details>")
        lines.append(f"<summary>展开原文证据（{len(blocks)} 块）</summary>")
        lines.append("")
        for b in blocks:
            lines.append(f"### {_block_heading(b)}")
            lines.append("")
            if b.text:
                lines.append(b.text.strip())
            if b.image_path:
                img_name = b.image_path.replace("\\", "/").split("/")[-1]
                lines.append("")
                lines.append(f"![[{img_name}]]")
            lines.append("")
        lines.append("</details>")
        lines.append("")

    md = "\n".join(lines)
    return {"markdown": md, "filename": f"{title}.md"}
