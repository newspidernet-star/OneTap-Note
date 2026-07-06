import pytest


@pytest.mark.anyio
async def test_match_and_generate_and_result(client, monkeypatch):
    result = {
        "corrected_text": "纠错",
        "summary": "摘要",
        "key_points": [{"point": "要点", "citations": ["S001"]}],
        "corrections": [],
    }

    def fake_match(sid, db):
        return []

    def fake_clear(sid, db):
        pass

    def fake_generate(sid, db, priority_material_ids=None):
        return result

    def fake_verify(r, sid, db):
        return {"valid": True, "invalid_ids": []}

    def fake_save(r, sid, db):
        from app.models import Summary
        s = Summary(
            session_id=sid,
            corrected_text=r["corrected_text"],
            summary_markdown=r["summary"],
            key_points=r["key_points"],
            citations=r["key_points"],
            unused_block_ids=[],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return s

    monkeypatch.setattr("app.api.summary.match_evidence", fake_match)
    monkeypatch.setattr("app.api.summary.clear_summary", fake_clear)
    monkeypatch.setattr("app.api.summary.generate_summary", fake_generate)
    monkeypatch.setattr("app.api.summary.verify_citations", fake_verify)
    monkeypatch.setattr("app.api.summary.save_summary", fake_save)

    s = await client.post("/api/sessions", json={"title": "T"})
    sid = s.json()["id"]

    r1 = await client.post(f"/api/summary/match/{sid}")
    assert r1.status_code == 200
    assert r1.json()["pairs_count"] == 0

    r2 = await client.post(f"/api/summary/generate/{sid}")
    assert r2.status_code == 200
    assert r2.json()["status"] == "completed"

    r3 = await client.get(f"/api/summary/result/{sid}")
    assert r3.status_code == 200
    data = r3.json()
    assert data["summary"] == "摘要"
    assert len(data["key_points"]) == 1
    assert data["key_points"][0]["point"] == "要点"


@pytest.mark.anyio
async def test_verify_endpoint(client, monkeypatch):
    def fake_clear(sid, db):
        pass

    def fake_generate(sid, db, priority_material_ids=None):
        return {"corrected_text": "", "summary": "", "key_points": [], "corrections": []}

    def fake_verify(r, sid, db):
        return {"valid": True, "invalid_ids": []}

    def fake_detect(r, sid, db):
        return []

    def fake_save(r, sid, db):
        from app.models import Summary
        s = Summary(
            session_id=sid,
            corrected_text=r["corrected_text"],
            summary_markdown=r["summary"],
            key_points=r["key_points"],
            citations=r["key_points"],
            unused_block_ids=[],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return s

    monkeypatch.setattr("app.api.summary.clear_summary", fake_clear)
    monkeypatch.setattr("app.api.summary.generate_summary", fake_generate)
    monkeypatch.setattr("app.api.summary.verify_citations", fake_verify)
    monkeypatch.setattr("app.api.summary.detect_unused_blocks", fake_detect)
    monkeypatch.setattr("app.api.summary.save_summary", fake_save)

    s = await client.post("/api/sessions", json={"title": "T"})
    sid = s.json()["id"]

    await client.post(f"/api/summary/generate/{sid}")

    resp = await client.post(f"/api/summary/verify/{sid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["citation_valid"] is True
    assert data["invalid_citations"] == []
    assert data["unused_block_ids"] == []


@pytest.mark.anyio
async def test_generate_waits_for_video_transcription(client):
    s = await client.post("/api/sessions", json={"title": "T"})
    sid = s.json()["id"]

    upload = await client.post(
        "/api/media/upload",
        data={"session_id": str(sid), "sort_order": "0"},
        files={"file": ("clip.mp4", b"fake-video", "video/mp4")},
    )
    assert upload.status_code == 200

    resp = await client.post(f"/api/summary/generate/{sid}")
    assert resp.status_code == 409
    assert "语音转写" in resp.json()["detail"]


@pytest.mark.anyio
async def test_generate_updates_title_on_first_summary_only(client, monkeypatch):
    result = {
        "corrected_text": "纠错文本",
        "summary": "关于电磁感应的摘要",
        "key_points": [{"point": "要点", "citations": ["S001"]}],
        "corrections": [],
    }

    def fake_clear(sid, db):
        pass

    def fake_generate(sid, db, priority_material_ids=None):
        return result

    def fake_verify(r, sid, db):
        return {"valid": True, "invalid_ids": []}

    def fake_save(r, sid, db):
        from app.models import Summary
        existing = db.query(Summary).filter_by(session_id=sid).first()
        if existing:
            db.delete(existing)
            db.flush()
        s = Summary(
            session_id=sid,
            corrected_text=r["corrected_text"],
            summary_markdown=r["summary"],
            key_points=r["key_points"],
            citations=r["key_points"],
            unused_block_ids=[],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return s

    monkeypatch.setattr("app.api.summary.clear_summary", fake_clear)
    monkeypatch.setattr("app.api.summary.generate_summary", fake_generate)
    monkeypatch.setattr("app.api.summary.verify_citations", fake_verify)
    monkeypatch.setattr("app.api.summary.save_summary", fake_save)
    monkeypatch.setattr("app.api.summary.generate_title", lambda text, db: "电磁感应")

    s = await client.post("/api/sessions", json={"title": "filename.mp4"})
    sid = s.json()["id"]

    r1 = await client.post(f"/api/summary/generate/{sid}")
    assert r1.status_code == 200

    sessions = await client.get("/api/sessions")
    session = next(s for s in sessions.json() if s["id"] == sid)
    assert session["title"] == "电磁感应"

    # Rename manually and regenerate; title should stay as manual rename.
    await client.patch(f"/api/sessions/{sid}", json={"title": "我的手写标题"})

    r2 = await client.post(f"/api/summary/generate/{sid}")
    assert r2.status_code == 200

    sessions2 = await client.get("/api/sessions")
    session2 = next(s for s in sessions2.json() if s["id"] == sid)
    assert session2["title"] == "我的手写标题"
