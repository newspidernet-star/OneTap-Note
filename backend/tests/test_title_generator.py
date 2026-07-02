import pytest
from unittest.mock import MagicMock

from app.services.title_generator import _clean_title, generate_title


def test_clean_title_removes_punctuation_and_quotes():
    assert _clean_title('"电磁感应定律"') == "电磁感应定律"
    assert _clean_title("法拉第定律。") == "法拉第定律"
    assert _clean_title("  楞次定律  ") == "楞次定律"
    assert _clean_title("A, B; C!") == "ABC"


def test_clean_title_truncates_long_text():
    long_text = "a" * 50
    assert len(_clean_title(long_text)) == 20


def test_generate_title_returns_none_without_api_key(db_session):
    result = generate_title("电磁感应定律是描述磁通量变化产生感应电动势的基本规律。", db_session)
    assert result is None


def test_generate_title_uses_deepseek(monkeypatch, db_session):
    from app.models import ApiSettings
    from app.services.crypto import encrypt

    db_session.add(ApiSettings(key="deepseek_api_key", encrypted_value=encrypt("sk-test")))
    db_session.commit()

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "  电磁感应原理  "}}]}

    monkeypatch.setattr("app.services.title_generator.httpx.post", lambda *a, **kw: FakeResponse())

    result = generate_title("电磁感应定律是描述磁通量变化产生感应电动势的基本规律。", db_session)
    assert result == "电磁感应原理"
