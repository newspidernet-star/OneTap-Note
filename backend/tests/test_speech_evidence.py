from app.models import EvidenceBlock, Session


def test_process_speech_creates_blocks(db_session):
    s = Session(title="T", status="processing", created_at="2025-01-01", updated_at="2025-01-01")
    db_session.add(s)
    db_session.commit()

    from app.models import Transcript, TranscriptSegment
    t = Transcript(session_id=s.id)
    db_session.add(t)
    db_session.commit()
    for start, end, spk, txt in [
        (0, 3, "讲师", "电磁感应现象"),
        (4, 8, "讲师", "法拉第定律"),
        (9, 12, "学生", "老师我有问题"),
    ]:
        db_session.add(TranscriptSegment(transcript_id=t.id, start_time=start, end_time=end, speaker=spk, text=txt))
    db_session.commit()

    from app.services.pipeline import _process_speech
    block_ids = _process_speech(s.id, db_session)
    assert len(block_ids) == 3
    assert block_ids[0] == "S001"

    blocks = db_session.query(EvidenceBlock).filter_by(session_id=s.id, type="speech").order_by(EvidenceBlock.timestamp).all()
    assert len(blocks) == 3
    assert blocks[0].speaker == "讲师"
    assert blocks[0].text == "电磁感应现象"
    assert blocks[1].block_id == "S002"
    assert blocks[2].speaker == "学生"
