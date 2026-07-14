import pytest
import json

from app.services.progress import clear_progress, finish_progress, get_progress, set_progress


def test_progress_tracks_stages_and_elapsed(monkeypatch):
    ticks = iter([100.0, 103.5, 106.0, 108.0, 109.0])
    monkeypatch.setattr("app.services.progress.time.time", lambda: next(ticks))

    set_progress(501, "download", "正在下载")
    set_progress(501, "transcribe", "正在转写")
    state = get_progress(501)

    assert state["stage"] == "transcribe"
    assert state["elapsed_seconds"] == 6.0
    assert state["completed_stages"][0]["duration_seconds"] == 3.5

    finish_progress(501, "完成")
    assert get_progress(501)["status"] == "done"


@pytest.mark.anyio
async def test_progress_endpoint(client):
    created = await client.post("/api/sessions", json={"title": "T"})
    session_id = created.json()["id"]

    response = await client.get(f"/api/sessions/{session_id}/progress")

    assert response.status_code == 200
    assert response.json()["status"] == "idle"


def test_clear_progress_removes_reused_session_state():
    set_progress(777, "transcribe", "正在听写")
    clear_progress(777)

    assert get_progress(777)["status"] == "idle"


def test_progress_writes_timing_only_metric(monkeypatch, tmp_path):
    metrics_path = tmp_path / "processing-runs.jsonl"
    monkeypatch.setenv("ONE_TAP_NOTE_COLLECT_METRICS", "1")
    monkeypatch.setenv("ONE_TAP_NOTE_METRICS_PATH", str(metrics_path))
    ticks = iter([200.0, 202.5, 205.0])
    monkeypatch.setattr("app.services.progress.time.time", lambda: next(ticks))

    set_progress(888, "download", "downloading", "https://secret.example/video")
    set_progress(888, "transcribe", "transcribing", "private note text")
    finish_progress(888, "done", "private result")

    record = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert record["status"] == "done"
    assert record["total_seconds"] == 5.0
    assert record["completed_stages"] == [
        {"stage": "download", "duration_seconds": 2.5},
        {"stage": "transcribe", "duration_seconds": 2.5},
    ]
    raw = metrics_path.read_text(encoding="utf-8")
    assert '"session_id"' not in raw
    assert "secret.example" not in raw
    assert "private" not in raw


def test_metric_write_failure_does_not_break_progress(monkeypatch, tmp_path):
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("blocked", encoding="utf-8")
    monkeypatch.setenv("ONE_TAP_NOTE_COLLECT_METRICS", "1")
    monkeypatch.setenv("ONE_TAP_NOTE_METRICS_PATH", str(blocker / "metrics.jsonl"))

    set_progress(204, "transcribing", "working")
    finish_progress(204)

    assert get_progress(204)["status"] == "done"