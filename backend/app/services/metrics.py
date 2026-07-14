from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from app.config import get_settings


_FALSE_VALUES = {"0", "false", "no", "off"}
logger = logging.getLogger("smart_scribe")


def metrics_enabled() -> bool:
    value = os.getenv("ONE_TAP_NOTE_COLLECT_METRICS", "1").strip().lower()
    return value not in _FALSE_VALUES


def processing_metrics_path() -> Path:
    override = os.getenv("ONE_TAP_NOTE_METRICS_PATH", "").strip()
    if override:
        return Path(override)
    return get_settings().storage_dir / "metrics" / "processing-runs.jsonl"


def append_processing_metric(state: dict[str, Any]) -> None:
    """Persist timing-only processing metrics without media, URLs, or note text."""
    if not metrics_enabled():
        return

    record = {
        "schema_version": 1,
        "run_id": state.get("run_id"),
        "status": state.get("status"),
        "started_at": state.get("started_at"),
        "finished_at": state.get("updated_at"),
        "total_seconds": state.get("total_seconds"),
        "completed_stages": [
            {
                "stage": item.get("stage"),
                "duration_seconds": item.get("duration_seconds"),
            }
            for item in state.get("completed_stages", [])
        ],
    }
    path = processing_metrics_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    except OSError as exc:
        # Diagnostics must never turn a successful media task into a failure.
        logger.warning("processing metrics write skipped: %s", exc)