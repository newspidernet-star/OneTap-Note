from dataclasses import dataclass, field
import logging
import re
import time

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EvidenceBlock, Material, Transcript, TranscriptSegment
from app.services.frame_extractor import extract_keyframes
from app.services.ocr import OcrResult, ocr_batch, ocr_image
from app.services.storage import resolve_storage_path, session_storage_dir

logger = logging.getLogger("smart_scribe")


@dataclass
class ProcessingResult:
    frames_count: int = 0
    ocr_pages_count: int = 0
    evidence_block_ids: list = field(default_factory=list)


_p_counters: dict[int, int] = {}
_s_counters: dict[int, int] = {}


def _init_p_counter(session_id: int, db: Session) -> None:
    existing = db.query(EvidenceBlock.block_id).filter(
        EvidenceBlock.session_id == session_id,
        EvidenceBlock.block_id.like("P%"),
    ).all()
    max_n = 0
    for (bid,) in existing:
        m = re.match(r"^P(\d+)$", (bid or "").strip())
        if m:
            max_n = max(max_n, int(m.group(1)))
    _p_counters[session_id] = max_n


def _next_p_id(session_id: int) -> str:
    _p_counters[session_id] = _p_counters.get(session_id, 0) + 1
    return f"P{_p_counters[session_id]:03d}"


def _next_s_id(session_id: int) -> str:
    _s_counters[session_id] = _s_counters.get(session_id, 0) + 1
    return f"S{_s_counters[session_id]:03d}"


def _init_s_counter(session_id: int, db: Session) -> None:
    existing = db.query(EvidenceBlock.block_id).filter(
        EvidenceBlock.session_id == session_id,
        EvidenceBlock.block_id.like("S%"),
    ).all()
    max_n = 0
    for (bid,) in existing:
        m = re.match(r"^S(\d+)$", (bid or "").strip())
        if m:
            max_n = max(max_n, int(m.group(1)))
    _s_counters[session_id] = max_n


def _process_video(material: Material, db: Session) -> tuple[int, int, list[str]]:
    d = session_storage_dir(material.session_id)
    frames_dir = d / "frames"
    video_path = resolve_storage_path(material.file_path)
    t0 = time.time()
    keyframes = extract_keyframes(video_path, str(frames_dir))
    logger.info(f"[FRAMES] session {material.session_id}: extracted {len(keyframes)} frames, {time.time()-t0:.2f}s")

    if not keyframes:
        # Fallback: use old extract_and_dedup if OpenCV keyframes failed
        from app.services.frame_extractor import extract_and_dedup
        frames = extract_and_dedup(video_path, str(frames_dir))
        return _build_video_blocks(frames, material, db)

    # OCR with incremental dedup: 先 OCR 所有帧，然后去重——文字大量重复的帧跳过
    t1 = time.time()
    frame_paths = [fp for (_, fp) in keyframes]
    results = ocr_batch(frame_paths, db)
    raw_ocr = []
    for idx, (ts, fp) in enumerate(keyframes):
        if idx < len(results) and results[idx].text.strip():
            logger.info(
                "[OCR] candidate frame idx=%d ts=%.2fs text_len=%d reason=ocr-text",
                idx, ts, len(results[idx].text.strip()),
            )
            raw_ocr.append((idx, ts, fp, results[idx]))
        else:
            logger.info("[OCR] candidate frame idx=%d ts=%.2fs reason=no-ocr-text", idx, ts)

    # 跨帧文字去重：如果当前帧和前一帧文字大量重合，只保留文字量更多的那个
    ocr_results = []
    skipped = 0
    for idx, ts, fp, result in raw_ocr:
        cur_text = result.text.strip()
        if ocr_results and cur_text:
            prev_text = ocr_results[-1][3].text.strip()
            overlap = len(set(cur_text) & set(prev_text)) / max(len(set(cur_text) | set(prev_text)), 1)
            if overlap > 0.85:
                # 高重合 → 合并（保留文字量更多的那个，更新时间戳为较晚的那个）
                if len(cur_text) > len(prev_text):
                    logger.info(
                        "[OCR] dedup replace prev_ts=%.2fs with ts=%.2fs overlap=%.3f prev_len=%d cur_len=%d",
                        ocr_results[-1][1], ts, overlap, len(prev_text), len(cur_text),
                    )
                    ocr_results[-1] = (idx, ts, fp, result)
                else:
                    logger.info(
                        "[OCR] dedup drop ts=%.2fs overlap=%.3f prev_len=%d cur_len=%d",
                        ts, overlap, len(prev_text), len(cur_text),
                    )
                skipped += 1
                continue
        logger.info("[OCR] keep frame idx=%d ts=%.2fs text_len=%d", idx, ts, len(cur_text))
        ocr_results.append((idx, ts, fp, result))

    logger.info(f"[OCR] session {material.session_id}: {len(raw_ocr)} frames OCR'd, {skipped} deduped, {len(ocr_results)} kept, {time.time()-t1:.2f}s")

    if not ocr_results:
        return len(keyframes), 0, []

    ocr_results.sort(key=lambda x: len(x[3].text), reverse=True)
    main_idx, main_ts, main_fp, main_result = ocr_results[0]
    main_text_len = len(main_result.text)

    blocks = []
    block_id = _next_p_id(material.session_id)
    eb = EvidenceBlock(
        block_id=block_id, session_id=material.session_id, material_id=material.id,
        type="video_frame", timestamp=main_ts, text=main_result.text,
        page_number=main_idx + 1, image_path=main_fp,
    )
    db.add(eb); blocks.append(block_id)

    for idx, ts, fp, result in ocr_results[1:]:
        if len(result.text) > main_text_len * 0.5:
            block_id = _next_p_id(material.session_id)
            eb = EvidenceBlock(
                block_id=block_id, session_id=material.session_id, material_id=material.id,
                type="video_frame", timestamp=ts, text=result.text,
                page_number=idx + 1, image_path=fp,
            )
            db.add(eb); blocks.append(block_id)

    db.flush()
    return len(keyframes), len(blocks), blocks


def _build_video_blocks(frames: list[str], material: Material, db: Session) -> tuple[int, int, list[str]]:
    results = ocr_batch(frames, db)
    ocr_results = []
    for idx, fp in enumerate(frames):
        if idx < len(results) and results[idx].text.strip():
            ocr_results.append((idx, fp, results[idx]))

    if not ocr_results:
        return len(frames), 0, []

    main_idx = max(range(len(ocr_results)), key=lambda i: len(ocr_results[i][2].text))
    main_frame = ocr_results[main_idx]

    blocks = []
    block_id = _next_p_id(material.session_id)
    eb = EvidenceBlock(
        block_id=block_id, session_id=material.session_id, material_id=material.id,
        type="video_frame", timestamp=float(main_frame[0]) * 3.0,
        text=main_frame[2].text, page_number=main_frame[0] + 1, image_path=main_frame[1],
    )
    db.add(eb); blocks.append(block_id)
    main_text_len = len(main_frame[2].text)

    for i, (idx, fp, result) in enumerate(ocr_results):
        if i == main_idx: continue
        if len(result.text) > main_text_len * 0.5:
            block_id = _next_p_id(material.session_id)
            eb = EvidenceBlock(
                block_id=block_id, session_id=material.session_id, material_id=material.id,
                type="video_frame", timestamp=float(idx) * 3.0,
                text=result.text, page_number=idx + 1, image_path=fp,
            )
            db.add(eb); blocks.append(block_id)

    db.flush()
    return len(frames), len(blocks), blocks


def _process_image(material: Material, db: Session) -> tuple[int, int, list[str]]:
    image_path = resolve_storage_path(material.file_path)
    t0 = time.time()
    result = ocr_image(image_path, db)
    logger.info(f"[OCR] session {material.session_id}: image OCR done, text len {len(result.text)}, {time.time()-t0:.2f}s")
    if not result.text.strip():
        return 1, 0, []
    block_id = _next_p_id(material.session_id)
    timestamp = float(material.sort_order) * 60.0
    eb = EvidenceBlock(
        block_id=block_id,
        session_id=material.session_id,
        material_id=material.id,
        type="image",
        timestamp=timestamp,
        text=result.text,
        page_number=material.sort_order + 1,
        image_path=image_path,
    )
    db.add(eb)
    return 1, 1, [block_id]


def _process_speech(session_id: int, db: Session) -> list[str]:
    transcripts = db.query(Transcript).filter_by(session_id=session_id).all()
    if not transcripts:
        return []
    _init_s_counter(session_id, db)

    block_ids = []
    for transcript in transcripts:
        segments = db.query(TranscriptSegment).filter_by(transcript_id=transcript.id).order_by(TranscriptSegment.start_time).all()
        for seg in segments:
            if not seg.text.strip():
                continue
            block_id = _next_s_id(session_id)
            eb = EvidenceBlock(
                block_id=block_id,
                session_id=session_id,
                material_id=transcript.material_id,
                type="speech",
                timestamp=seg.start_time,
                end_timestamp=seg.end_time,
                speaker=seg.speaker,
                text=seg.text,
            )
            db.add(eb)
            db.flush()
            block_ids.append(block_id)
    db.commit()
    return block_ids


def _commit_with_retry(db: Session, session_id: int, op: str) -> None:
    import sqlite3
    for attempt in range(5):
        try:
            db.commit()
            return
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < 4:
                time.sleep(1 + attempt * 0.5)
                continue
            raise


def process_session(session_id: int, db: Session) -> ProcessingResult:
    t_start = time.time()
    materials = db.query(Material).filter_by(session_id=session_id).order_by(Material.sort_order).all()
    logger.info(f"[PROC] session {session_id}: start, materials={len(materials)}")
    _init_p_counter(session_id, db)
    result = ProcessingResult()
    all_blocks = []
    for m in materials:
        if m.status != "pending":
            continue
        if m.type == "video":
            if get_settings().auto_video_ocr:
                fc, oc, blocks = _process_video(m, db)
            else:
                logger.info(
                    "[FRAMES] session %s: automatic video OCR skipped (fast mode); manual frame capture remains available",
                    session_id,
                )
                fc, oc, blocks = 0, 0, []
            m.status = "done"
        elif m.type == "image":
            fc, oc, blocks = _process_image(m, db)
            m.status = "done"
        else:
            continue  # audio stays pending, not marked done
        result.frames_count += fc
        result.ocr_pages_count += oc
        all_blocks.extend(blocks)
        # 每处理完一个素材就提交，避免长时间持锁
        _commit_with_retry(db, session_id, "material")
    result.evidence_block_ids = all_blocks
    logger.info(f"[OK] session {session_id}: done, {result.frames_count} frames, {result.ocr_pages_count} blocks, {time.time()-t_start:.2f}s")
    return result
