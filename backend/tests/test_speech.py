from app.api.speech import _friendly_transcription_error
from app.services.qwen_asr import _is_retriable_public_file_error, _parse_filetrans_response


def test_public_file_server_error_is_retriable():
    error = ValueError(
        "ASR 任务失败: {'code': 'SERVER_ERROR', "
        "'file_url': 'https://example.trycloudflare.com/static/media/audio.mp3'}"
    )
    assert _is_retriable_public_file_error(error) is True
    assert _friendly_transcription_error(error) == (
        "语音服务暂时无法读取音频，请稍后重试。若持续失败，请检查网络代理后重新处理。"
    )


def test_unrelated_asr_error_is_not_exposed_to_ui():
    error = ValueError("ASR 任务失败: {'request_id': 'secret-debug-id'}")
    assert _is_retriable_public_file_error(error) is False
    assert _friendly_transcription_error(error) == (
        "语音转写失败，请稍后重试；若仍失败，请检查转写设置和网络。"
    )


def test_parse_filetrans_response_sentences():
    raw = {
        "transcripts": [
            {
                "speaker": "说话人1",
                "text": "今天讲电磁感应。",
                "sentences": [
                    {"begin_time": 1000, "end_time": 3000, "text": "今天讲电磁感应。"},
                ],
            }
        ]
    }
    segs = _parse_filetrans_response(raw)
    assert len(segs) == 1
    assert segs[0]["start_time"] == 1.0
    assert segs[0]["end_time"] == 3.0
    assert segs[0]["speaker"] == "说话人1"
    assert segs[0]["text"] == "今天讲电磁感应。"


def test_parse_filetrans_response_with_speaker_id():
    """Fun‑ASR diarization returns speaker_id on each sentence."""
    raw = {
        "transcripts": [
            {
                "sentences": [
                    {"begin_time": 0, "end_time": 2000, "text": "你好。", "speaker_id": 0},
                    {"begin_time": 2500, "end_time": 5000, "text": "大家好。", "speaker_id": 1},
                ],
            }
        ]
    }
    segs = _parse_filetrans_response(raw)
    assert len(segs) == 2
    assert segs[0]["speaker"] == "0"
    assert segs[1]["speaker"] == "1"


def test_transcribe_stores_in_db(db_session, monkeypatch, tmp_path):
    from app.services.qwen_asr import transcribe
    from app.services.crypto import encrypt
    from app.models import ApiSettings, Transcript, TranscriptSegment

    db_session.add(ApiSettings(key="dashscope_api_key", encrypted_value=encrypt("test-key")))
    db_session.commit()

    fake_audio = tmp_path / "fake.wav"
    fake_audio.write_bytes(b"fake audio content" * 10)

    fake_segs = [
        {"start_time": 0.0, "end_time": 2.0, "speaker": "说话人1", "text": "hello world"},
    ]

    monkeypatch.setattr("app.services.qwen_asr._ensure_mp3", lambda p: p)
    monkeypatch.setattr("app.services.qwen_asr._transcribe_async", lambda *a, **kw: fake_segs)

    segments = transcribe(str(fake_audio), session_id=42, db=db_session)

    assert len(segments) == 1
    assert segments[0]["text"] == "hello world"

    t = db_session.query(Transcript).filter_by(session_id=42).first()
    assert t is not None
    segs = db_session.query(TranscriptSegment).filter_by(transcript_id=t.id).all()
    assert len(segs) == 1
    assert segs[0].text == "hello world"
