import pytest

from app.api.summary import _export_evidence, _export_note, _export_transcript
from app.models import EvidenceBlock, Summary


def test_export_note_is_clean_and_evidence_stays_separate():
    summary = Summary(
        corrected_text="打开导入窗口，然后勾选图像序列。",
        summary_markdown="## 一句话结论\n\n只选第一张图片并勾选图像序列。\n\n## 操作步骤\n\n1. 打开导入窗口。",
        key_points=[{"point": "正确导入图像序列", "citations": ["S001", "P001"]}],
        unused_block_ids=["S002"],
    )
    speech = EvidenceBlock(block_id="S001", session_id=1, type="speech", timestamp=45, speaker="讲师", text="只选第一张图片")
    frame = EvidenceBlock(block_id="P001", session_id=1, type="video_frame", timestamp=56, text="图像序列")

    note = _export_note("Premiere 导入图像序列", "2026-07-07", summary)
    transcript = _export_transcript("Premiere 导入图像序列", "2026-07-07", summary, [speech, frame])
    evidence = _export_evidence("Premiere 导入图像序列", "2026-07-07", summary, [speech, frame])

    assert "## 操作步骤" in note
    assert "S001" not in note
    assert "证据索引" not in note
    assert "详细原文" not in note
    assert "语音转写（已纠错）" in transcript
    assert "图像序列" in transcript
    assert "`S001`" in evidence
    assert "未被正文引用" in evidence


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
    monkeypatch.setattr("app.api.summary.review_summary_completeness", lambda result, sid, db: result)
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
    monkeypatch.setattr("app.api.summary.review_summary_completeness", lambda result, sid, db: result)
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
    monkeypatch.setattr("app.api.summary.review_summary_completeness", lambda result, sid, db: result)
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
