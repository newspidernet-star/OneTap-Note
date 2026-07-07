import pytest

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
