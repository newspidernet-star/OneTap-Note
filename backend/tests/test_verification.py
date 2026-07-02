from app.models import EvidenceBlock, Session
from app.services.summarizer import (
    clear_summary,
    detect_unused_blocks,
    save_summary,
    verify_citations,
)


def test_verify_citations_all_valid(db_session):
    s = Session(title="T", status="done", created_at="2025-01-01", updated_at="2025-01-01", id=99)
    db_session.add(s)
    db_session.add(EvidenceBlock(block_id="S001", session_id=99, material_id=1, type="speech", timestamp=0, text="a"))
    db_session.add(EvidenceBlock(block_id="P001", session_id=99, material_id=1, type="screen", timestamp=0, text="b"))
    db_session.commit()

    result = {
        "key_points": [
            {"point": "x", "citations": ["S001", "P001"]},
        ]
    }
    v = verify_citations(result, 99, db_session)
    assert v["valid"] is True
    assert len(v["invalid_ids"]) == 0


def test_verify_citations_fake_id(db_session):
    s = Session(title="T", status="done", created_at="2025-01-01", updated_at="2025-01-01", id=100)
    db_session.add(s)
    db_session.add(EvidenceBlock(block_id="S001", session_id=100, material_id=1, type="speech", timestamp=0, text="a"))
    db_session.commit()

    result = {
        "key_points": [{"point": "x", "citations": ["S001", "P999"]}],
        "corrected_text": "x [P999]",
        "summary": "x [P999]",
    }
    v = verify_citations(result, 100, db_session)
    assert v["valid"] is False
    assert "P999" in v["invalid_ids"]


def test_detect_unused_blocks(db_session):
    s = Session(title="T", status="done", created_at="2025-01-01", updated_at="2025-01-01", id=101)
    db_session.add(s)
    db_session.add(EvidenceBlock(block_id="S001", session_id=101, material_id=1, type="speech", timestamp=0, text="a"))
    db_session.add(EvidenceBlock(block_id="S002", session_id=101, material_id=1, type="speech", timestamp=1, text="b"))
    db_session.commit()

    result = {"key_points": [{"point": "x", "citations": ["S001"]}]}
    unused = detect_unused_blocks(result, 101, db_session)
    assert "S002" in unused
    assert "S001" not in unused


def test_save_and_clear_summary(db_session):
    s = Session(title="T", status="done", created_at="2025-01-01", updated_at="2025-01-01", id=102)
    db_session.add(s)
    db_session.add(EvidenceBlock(block_id="S001", session_id=102, material_id=1, type="speech", timestamp=0, text="a"))
    db_session.add(EvidenceBlock(block_id="S002", session_id=102, material_id=1, type="speech", timestamp=1, text="b"))
    db_session.commit()

    result = {
        "corrected_text": "纠错后文字",
        "summary": "摘要内容",
        "key_points": [{"point": "p", "citations": ["S001"]}],
        "corrections": [{"offset": 0, "old": "x", "new": "y"}],
    }
    summary = save_summary(result, 102, db_session)
    assert summary.summary_markdown == "摘要内容"
    assert "p" in str(summary.key_points)
    assert "S002" in str(summary.unused_block_ids)

    clear_summary(102, db_session)
    from app.models import Summary
    assert db_session.query(Summary).filter_by(session_id=102).first() is None
