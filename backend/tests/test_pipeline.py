from io import BytesIO

from app.models import EvidenceBlock
from app.services.ocr import OcrResult


async def test_process_image_creates_evidence(client, monkeypatch):
    fake = OcrResult(text="法拉第电磁感应定律")
    monkeypatch.setattr("app.services.pipeline.ocr_image", lambda path, db: fake)

    s = await client.post("/api/sessions", json={"title": "T"})
    sid = s.json()["id"]
    await client.post(
        "/api/media/upload",
        data={"session_id": sid, "sort_order": 0},
        files={"file": ("slide.png", BytesIO(b"fake"), "image/png")},
    )

    resp = await client.post(f"/api/media/session/{sid}/process")
    assert resp.status_code == 200
    assert resp.json()["ocr_pages_count"] == 1
    assert "P001" in resp.json()["evidence_block_ids"]

    evidence = await client.get(f"/api/media/evidence/{sid}")
    assert evidence.status_code == 200
    assert len(evidence.json()) == 1
    assert evidence.json()[0]["text"] == "法拉第电磁感应定律"
    assert evidence.json()[0]["type"] == "image"


def test_video_material_skips_automatic_frames_by_default(db, tmp_path, monkeypatch):
    from app.services.pipeline import process_session
    from app.models import Session, Material

    session = Session(title="test", status="created", created_at="now", updated_at="now")
    db.add(session)
    db.commit()

    # Create a tiny valid mp4 via ffmpeg
    video_path = tmp_path / "sample.mp4"
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=5:size=320x240:rate=1",
            "-pix_fmt",
            "yuv420p",
            str(video_path),
        ],
        check=True,
        capture_output=True,
    )

    material = Material(
        session_id=session.id,
        type="video",
        source="upload",
        file_path=str(video_path),
        status="pending",
    )
    db.add(material)
    db.commit()

    result = process_session(session.id, db)
    db.refresh(material)

    assert material.status == "done"
    assert result.frames_count == 0
    assert result.ocr_pages_count == 0
    blocks = db.query(EvidenceBlock).filter_by(session_id=session.id).all()
    assert blocks == []
