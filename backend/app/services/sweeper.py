"""后台清扫线程：ephemeral 模式下，定期删除心跳超时的会话。

策略：
- 每 30 秒扫一次 sessions 表
- 若 last_seen_at 距今超过 grace（ephemeral_ttl，默认 60s）→ 删该会话所有 DB 行 + 媒体目录
- 保护：status=processing 且 last_seen_at < 1 小时 → 不删（避免打断正在跑的 ffmpeg/ASR/总结）
- 卡死保护：last_seen_at > 1 小时 → 无论状态都删
"""
import logging
import shutil
import threading
import time
from datetime import datetime, timezone

from app.config import get_settings
from app.database import SessionLocal
from app.models import (
    EvidenceBlock, Material, Match, Session as SessionModel,
    Summary, Transcript, TranscriptSegment,
)

logger = logging.getLogger("smart_scribe")

_SWEEPER_STARTED = False
_LOCK = threading.Lock()


def purge_session(session_id: int) -> None:
    """同步彻底删除一个会话的 DB 记录 + 媒体文件。"""
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
        logger.info("[session %s] ephemeral purge: 已删除", session_id)
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


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _sweep_once() -> None:
    """扫一次：删掉所有心跳超时的会话。"""
    settings = get_settings()
    grace = settings.ephemeral_ttl
    now = datetime.now(timezone.utc)
    hard_limit = 3600  # 1 小时，无论状态都删

    db = SessionLocal()
    try:
        sessions = db.query(SessionModel).all()
        to_delete: list[tuple[int, float]] = []
        for s in sessions:
            last = _parse_iso(s.last_seen_at)
            if last is None:
                # 没有心跳字段（旧会话 / 刚迁移）→ 用 updated_at 兜底
                last = _parse_iso(s.updated_at)
            if last is None:
                continue
            # 时区对齐：last 可能带 tz 也可能不带
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            age = (now - last).total_seconds()
            if age < grace:
                continue
            # 超过 grace → 候选删除
            if age > hard_limit:
                to_delete.append((s.id, age))
                continue
            # 在 grace ~ hard_limit 之间：保护 processing
            if s.status == "processing":
                continue
            to_delete.append((s.id, age))
    finally:
        db.close()

    for sid, age in to_delete:
        logger.info("[session %s] sweeper: 心跳超时（age=%.0fs, grace=%ss）→ 删除",
                    sid, age, grace)
        purge_session(sid)


def _sweep_loop() -> None:
    while True:
        try:
            _sweep_once()
        except Exception as e:
            logger.warning("sweeper loop error: %s", e)
        time.sleep(30)


def start_sweeper() -> None:
    """启动后台清扫线程（仅 ephemeral=true 时；进程级单例）。"""
    global _SWEEPER_STARTED
    settings = get_settings()
    if not settings.ephemeral:
        return
    with _LOCK:
        if _SWEEPER_STARTED:
            return
        _SWEEPER_STARTED = True
        t = threading.Thread(target=_sweep_loop, daemon=True, name="ephemeral-sweeper")
        t.start()
        logger.info("ephemeral sweeper 已启动: grace=%ss, 扫描间隔=30s",
                    settings.ephemeral_ttl)
