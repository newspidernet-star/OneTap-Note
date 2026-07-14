from __future__ import annotations

from copy import deepcopy
from threading import Lock
import time
from uuid import uuid4

from app.services.metrics import append_processing_metric


_lock = Lock()
_states: dict[int, dict] = {}


def set_progress(
    session_id: int,
    stage: str,
    label: str,
    detail: str = "",
    *,
    reset: bool = False,
) -> None:
    now = time.time()
    with _lock:
        current = _states.get(session_id)
        if reset or not current or current.get("status") in {"done", "error"}:
            _states[session_id] = {
                "run_id": uuid4().hex,
                "session_id": session_id,
                "status": "processing",
                "stage": stage,
                "label": label,
                "detail": detail,
                "started_at": now,
                "stage_started_at": now,
                "updated_at": now,
                "completed_stages": [],
            }
            return

        if current["stage"] != stage:
            current["completed_stages"].append({
                "stage": current["stage"],
                "label": current["label"],
                "duration_seconds": round(now - current["stage_started_at"], 1),
            })
            current["stage"] = stage
            current["stage_started_at"] = now
        current.update({
            "status": "processing",
            "label": label,
            "detail": detail,
            "updated_at": now,
        })


def finish_progress(session_id: int, label: str = "处理完成", detail: str = "") -> None:
    _finish(session_id, "done", label, detail)


def fail_progress(session_id: int, detail: str) -> None:
    _finish(session_id, "error", "处理失败", detail)


def clear_progress(session_id: int) -> None:
    with _lock:
        _states.pop(session_id, None)


def _finish(session_id: int, status: str, label: str, detail: str) -> None:
    now = time.time()
    snapshot = None
    with _lock:
        current = _states.get(session_id)
        if not current:
            current = {
                "run_id": uuid4().hex,
                "session_id": session_id,
                "started_at": now,
                "stage_started_at": now,
                "completed_stages": [],
            }
            _states[session_id] = current
        if current.get("stage") and current.get("status") == "processing":
            current["completed_stages"].append({
                "stage": current["stage"],
                "label": current["label"],
                "duration_seconds": round(now - current["stage_started_at"], 1),
            })
        current.update({
            "status": status,
            "stage": status,
            "label": label,
            "detail": detail,
            "stage_started_at": now,
            "updated_at": now,
            "total_seconds": round(now - current["started_at"], 1),
        })
        snapshot = deepcopy(current)
    append_processing_metric(snapshot)


def get_progress(session_id: int) -> dict:
    now = time.time()
    with _lock:
        current = deepcopy(_states.get(session_id))
    if not current:
        return {
            "session_id": session_id,
            "status": "idle",
            "stage": "idle",
            "label": "等待处理",
            "detail": "",
            "elapsed_seconds": 0,
            "stage_elapsed_seconds": 0,
            "completed_stages": [],
        }
    current["elapsed_seconds"] = round(now - current["started_at"], 1)
    current["stage_elapsed_seconds"] = round(now - current["stage_started_at"], 1)
    return current
