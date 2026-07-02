import math
from collections import Counter
from sqlalchemy.orm import Session
from app.models import EvidenceBlock, Match


def time_similarity(a_time: float, b_time: float, window: float = 120) -> float:
    diff = abs(a_time - b_time)
    if diff >= window:
        return 0.0
    return 1.0 - (diff / window)


def _tokenize(text: str) -> set[str]:
    try:
        import jieba
        return set(jieba.cut(text))
    except ImportError:
        return set(text)


def jaccard_similarity(text_a: str, text_b: str) -> float:
    set_a = _tokenize(text_a)
    set_b = _tokenize(text_b)
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def _tf_idf_cosine(a: str, b: str) -> float:
    tokens_a = list(_tokenize(a))
    tokens_b = list(_tokenize(b))
    if not tokens_a or not tokens_b:
        return 0.0
    counter_a = Counter(tokens_a)
    counter_b = Counter(tokens_b)
    all_terms = set(counter_a) | set(counter_b)
    vec_a = [counter_a.get(t, 0) * 1.0 / len(tokens_a) for t in all_terms]
    vec_b = [counter_b.get(t, 0) * 1.0 / len(tokens_b) for t in all_terms]
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def match_score(s_block: EvidenceBlock, p_block: EvidenceBlock) -> float:
    ts = time_similarity(s_block.timestamp, p_block.timestamp)
    js = jaccard_similarity(s_block.text, p_block.text)
    ss = _tf_idf_cosine(s_block.text, p_block.text)
    return 0.35 * ts + 0.30 * js + 0.35 * ss


def match_evidence(session_id: int, db: Session) -> list[Match]:
    s_blocks = db.query(EvidenceBlock).filter_by(session_id=session_id, type="speech").all()
    p_blocks = db.query(EvidenceBlock).filter(
        EvidenceBlock.session_id == session_id,
        EvidenceBlock.type.in_(["video_frame", "image", "document", "screen"]),
    ).all()
    db.query(Match).filter(Match.speech_block_id.in_([s.id for s in s_blocks])).delete(synchronize_session=False)
    db.flush()
    matches = []
    for s in s_blocks:
        for p in p_blocks:
            score = match_score(s, p)
            if score > 0.6:
                m = Match(
                    speech_block_id=s.id,
                    screen_block_id=p.id,
                    score=score,
                    time_sim=time_similarity(s.timestamp, p.timestamp),
                    keyword_sim=jaccard_similarity(s.text, p.text),
                    semantic_sim=_tf_idf_cosine(s.text, p.text),
                )
                db.add(m)
                db.flush()
                matches.append(m)
    db.commit()
    return matches
