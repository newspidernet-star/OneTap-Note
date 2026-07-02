from app.models import EvidenceBlock, Match
from app.services.matcher import (
    jaccard_similarity,
    match_evidence,
    match_score,
    time_similarity,
)


def test_time_similarity_perfect():
    assert time_similarity(10, 10) == 1.0


def test_time_similarity_outside_window():
    assert time_similarity(0, 200) == 0.0


def test_time_similarity_half():
    assert time_similarity(0, 60) == 0.5


def test_jaccard_similarity():
    assert jaccard_similarity("电磁感应 定律 法拉第", "法拉第 电磁感应") > 0.5
    assert jaccard_similarity("电磁感应", "分子生物学") < 0.1


def test_match_score():
    s = EvidenceBlock(
        block_id="S001", session_id=1, material_id=1, type="speech",
        timestamp=10.0, speaker="讲师", text="电磁感应定律 法拉第 提出"
    )
    p = EvidenceBlock(
        block_id="P001", session_id=1, material_id=1, type="screen",
        timestamp=15.0, text="法拉第电磁感应定律 磁通量"
    )
    score = match_score(s, p)
    assert 0.0 <= score <= 1.0
    assert score > 0.4


def test_match_evidence(db_session):
    import random
    s = EvidenceBlock(block_id=f"S001_{random.randint(1,9999)}", session_id=1, material_id=1, type="speech", timestamp=10.0, speaker="讲师", text="电磁感应定律 磁通量")
    p = EvidenceBlock(block_id=f"P001_{random.randint(1,9999)}", session_id=1, material_id=1, type="screen", timestamp=12.0, text="电磁感应 法拉第 磁通量")
    db_session.add_all([s, p])
    db_session.commit()

    matches = match_evidence(1, db_session)
    assert len(matches) > 0
    assert matches[0].score > 0


def test_match_evidence_pairs_speech_with_all_material_types(db):
    from app.models import Session

    session = Session(title="test", status="created", created_at="now", updated_at="now")
    db.add(session)
    db.commit()

    s1 = EvidenceBlock(
        block_id="S001",
        session_id=session.id,
        type="speech",
        timestamp=0.0,
        text="shared content",
    )
    v1 = EvidenceBlock(
        block_id="V001",
        session_id=session.id,
        type="video_frame",
        timestamp=1.0,
        text="shared content",
    )
    i1 = EvidenceBlock(
        block_id="I001",
        session_id=session.id,
        type="image",
        timestamp=2.0,
        text="shared content",
    )
    d1 = EvidenceBlock(
        block_id="D001",
        session_id=session.id,
        type="document",
        timestamp=3.0,
        text="shared content",
    )
    scr1 = EvidenceBlock(
        block_id="SCR001",
        session_id=session.id,
        type="screen",
        timestamp=4.0,
        text="shared content",
    )
    db.add_all([s1, v1, i1, d1, scr1])
    db.commit()

    match_evidence(session.id, db)
    matches = db.query(Match).all()
    screen_block_ids = {m.screen_block_id for m in matches}

    assert v1.id in screen_block_ids
    assert i1.id in screen_block_ids
    assert d1.id in screen_block_ids
    assert scr1.id in screen_block_ids
