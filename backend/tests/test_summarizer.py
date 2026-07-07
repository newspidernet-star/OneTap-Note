from unittest.mock import MagicMock, patch

import pytest

from app.models import ApiSettings, EvidenceBlock, Match
from app.services.summarizer import build_prompt, call_deepseek, generate_summary, review_summary_completeness


def test_build_prompt():
    s = EvidenceBlock(block_id="S001", session_id=1, material_id=1, type="speech", timestamp=10.0, speaker="讲师", text="电磁感应定律")
    s.id = 1
    p = EvidenceBlock(block_id="P001", session_id=1, material_id=1, type="screen", timestamp=12.0, text="法拉第电磁感应 磁通量变化")
    p.id = 2
    m = Match(score=0.8, time_sim=0.95, keyword_sim=0.6, semantic_sim=0.7)
    m.speech_block_id = 1
    m.screen_block_id = 2
    prompt = build_prompt([s, p], [m])
    assert "S001" in prompt
    assert "P001" in prompt
    assert "电磁感应" in prompt
    assert "语音转写原文" in prompt
    assert "匹配关联" in prompt
    assert "[S001] ↔ [P001]" in prompt
    assert "0.80" in prompt
    assert "不要按视频顺序复述" in prompt
    assert "正文不显示 S/P 证据 ID" in prompt
    assert "显式清单必须保真" in prompt
    assert "全部 N 条" in prompt
    assert "不要自行生成行动优先级" in prompt
    assert "保持清单原始顺序" in prompt


def test_call_deepseek_mocked(monkeypatch):
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": '{"corrected_text":"测试纠错","summary":"测试摘要","key_points":[{"point":"要点","citations":["S001"]}],"corrections":[{"offset":0,"old":"测试","new":"测验"}]}'}}]
    }
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json = MagicMock(return_value=fake_response.json.return_value)

    monkeypatch.setattr("app.services.summarizer.decrypt", lambda x: "sk-test")

    db = MagicMock()
    fake_settings = ApiSettings(key="deepseek_api_key", encrypted_value="enc")
    db.query.return_value.filter_by.return_value.first.return_value = fake_settings

    with patch("httpx.post", return_value=fake_resp):
        result = call_deepseek("test prompt", db)
    assert result["corrected_text"] == "测试纠错"
    assert result["summary"] == "测试摘要"
    assert len(result["key_points"]) == 1


def test_call_deepseek_no_key():
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = None
    with pytest.raises(ValueError, match="未配置"):
        call_deepseek("test prompt", db)


def test_call_deepseek_json_fenced(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = {
        "choices": [{"message": {"content": '```json\n{"corrected_text":"纠错","summary":"摘要","key_points":[],"corrections":[]}\n```'}}]
    }
    monkeypatch.setattr("app.services.summarizer.decrypt", lambda x: "sk-test")
    db = MagicMock()
    fake_settings = ApiSettings(key="deepseek_api_key", encrypted_value="enc")
    db.query.return_value.filter_by.return_value.first.return_value = fake_settings

    with patch("httpx.post", return_value=fake_resp):
        result = call_deepseek("test prompt", db)
    assert result["corrected_text"] == "纠错"


def test_generate_summary_integration(monkeypatch, db_session):
    db_session.add(ApiSettings(key="deepseek_api_key", encrypted_value="enc", is_required=True))
    db_session.commit()

    monkeypatch.setattr("app.services.summarizer.decrypt", lambda x: "sk-test")

    s = EvidenceBlock(block_id="S001", session_id=1, material_id=1, type="speech", timestamp=10.0, speaker="讲师", text="电磁感应定律")
    p = EvidenceBlock(block_id="P001", session_id=1, material_id=1, type="screen", timestamp=12.0, text="法拉第电磁感应")
    db_session.add_all([s, p])
    db_session.commit()

    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = {
        "choices": [{"message": {"content": '{"corrected_text":"电磁感应定律","summary":"测试摘要","key_points":[{"point":"要点1","citations":["S001","P001"]}],"corrections":[]}'}}]
    }

    with patch("httpx.post", return_value=fake_resp):
        result = generate_summary(1, db_session)
    assert result["summary"] == "测试摘要"
    assert len(result["key_points"]) == 1
    assert result["key_points"][0]["point"] == "要点1"


def test_generate_summary_no_blocks(db_session):
    with pytest.raises(ValueError, match="无证据块"):
        generate_summary(999, db_session)


def test_completeness_review_merges_revised_note(db_session, monkeypatch):
    db_session.add(EvidenceBlock(
        block_id="S001",
        session_id=1,
        type="speech",
        timestamp=0,
        text="这里有三条建议：第一专注，第二复盘，第三执行。",
    ))
    db_session.commit()
    initial = {
        "corrected_text": "完整原文",
        "summary": "## 建议\n\n只有两条。",
        "key_points": [{"point": "两条建议", "citations": ["S001"]}],
    }
    monkeypatch.setattr(
        "app.services.summarizer._call_deepseek_with_system",
        lambda prompt, db, system: {
            "revised": True,
            "summary": "## 完整清单\n\n1. 专注\n2. 复盘\n3. 执行",
            "key_points": [{"point": "三条建议", "citations": ["S001"]}],
            "issues": ["补回第 3 条"],
        },
    )

    reviewed = review_summary_completeness(initial, 1, db_session)

    assert reviewed["corrected_text"] == "完整原文"
    assert "3. 执行" in reviewed["summary"]
    assert reviewed["_review_revised"] is True


def test_summary_cites_video_frame_and_image_blocks(db_session, monkeypatch):
    from app.models import Session

    session = Session(title="test", status="created", created_at="now", updated_at="now")
    db_session.add(session)
    db_session.commit()

    s1 = EvidenceBlock(
        block_id="S001",
        session_id=session.id,
        material_id=1,
        type="speech",
        timestamp=0.0,
        text="电磁感应",
    )
    v1 = EvidenceBlock(
        block_id="V001",
        session_id=session.id,
        material_id=1,
        type="video_frame",
        timestamp=1.0,
        text="法拉第定律",
    )
    i1 = EvidenceBlock(
        block_id="I001",
        session_id=session.id,
        material_id=1,
        type="image",
        timestamp=2.0,
        text="线圈图片",
    )
    db_session.add_all([s1, v1, i1])
    db_session.commit()

    fake_result = {
        "summary": "本课讲电磁感应。",
        "key_points": [
            {"point": "法拉第定律", "citations": ["V001", "I001"]},
        ],
        "corrected_text": "电磁感应",
        "corrections": [],
    }

    monkeypatch.setattr("app.services.summarizer.decrypt", lambda x: "sk-test")
    db_session.add(ApiSettings(key="deepseek_api_key", encrypted_value="enc", is_required=True))
    db_session.commit()

    with patch("app.services.summarizer.call_deepseek", return_value=fake_result) as mock_call:
        result = generate_summary(session.id, db_session)

    prompt = mock_call.call_args[0][0]
    assert "V001" in prompt
    assert "I001" in prompt
    assert "法拉第定律" in prompt
    assert "线圈图片" in prompt
    assert result["summary"] == "本课讲电磁感应。"
    assert any("V001" in kp.get("citations", []) for kp in result["key_points"])
    assert any("I001" in kp.get("citations", []) for kp in result["key_points"])


def test_priority_materials_are_marked_in_prompt(db_session):
    s = EvidenceBlock(
        block_id="S001",
        session_id=1,
        material_id=7,
        type="speech",
        timestamp=10.0,
        text="补充素材里的关键信息",
    )
    p = EvidenceBlock(
        block_id="P001",
        session_id=1,
        material_id=7,
        type="video_frame",
        timestamp=12.0,
        text="GitHub 项目地址 github.com/newspidernet-star/smart-scribe",
    )
    prompt = build_prompt([s, p], [], priority_material_ids={7})
    assert "用户重点追加" in prompt
    assert "必须吸收" in prompt
    assert "P001" in prompt


def test_generate_summary_appends_extracted_links(db_session, monkeypatch):
    block = EvidenceBlock(
        block_id="P001",
        session_id=1,
        material_id=1,
        type="video_frame",
        timestamp=1.0,
        text="项目地址 github.com/newspidernet-star/smart-scribe",
    )
    db_session.add(block)
    db_session.commit()

    monkeypatch.setattr(
        "app.services.summarizer.call_deepseek",
        lambda prompt, db: {
            "corrected_text": "",
            "summary": "这是一个项目介绍。",
            "key_points": [],
            "corrections": [],
        },
    )

    result = generate_summary(1, db_session)
    assert "来源链接" in result["summary"]
    assert "github.com/newspidernet-star/smart-scribe" in result["summary"]
