from app.models import EvidenceBlock, Material, Session


def test_create_session(db_session):
    s = Session(title="Test", status="created", created_at="2025-01-01", updated_at="2025-01-01")
    db_session.add(s)
    db_session.commit()

    assert s.id is not None
    assert s.title == "Test"


def test_session_material_relationship(db_session):
    s = Session(title="Test", status="created", created_at="2025-01-01", updated_at="2025-01-01")
    db_session.add(s)
    db_session.commit()

    m = Material(session_id=s.id, type="video", source="local_file", file_path="/tmp/x.mp4", sort_order=0)
    db_session.add(m)
    db_session.commit()

    eb = EvidenceBlock(
        block_id="P001",
        session_id=s.id,
        material_id=m.id,
        type="screen",
        timestamp=12.5,
        text="测试OCR文本",
        page_number=1,
        image_path="/tmp/frame_001.jpg",
    )
    db_session.add(eb)
    db_session.commit()

    assert db_session.query(Session).count() == 1
    assert db_session.query(Material).count() == 1
    assert db_session.query(EvidenceBlock).count() == 1
    assert db_session.query(EvidenceBlock).first().block_id == "P001"