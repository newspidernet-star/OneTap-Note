from unittest.mock import MagicMock, patch

from app.services.ocr import OcrResult, ocr_batch


def test_ocr_result_dataclass():
    r = OcrResult(text="测试", boxes=[[0, 0]], scores=[0.95])
    assert r.text == "测试"
    assert r.scores == [0.95]


def test_ocr_local_calls_paddleocr(tmp_path, monkeypatch):
    img = tmp_path / "x.jpg"
    img.write_bytes(b"fake")

    fake_settings = MagicMock()
    fake_settings.ocr_mode = "local"
    monkeypatch.setattr("app.services.ocr.get_settings", lambda: fake_settings)

    fake_result = {
        "rec_texts": ["测试文本"],
        "rec_scores": [0.99],
        "dt_polys": [[[0, 0], [1, 0], [1, 1], [0, 1]]],
    }
    fake_ocr = MagicMock()
    fake_ocr.predict.return_value = [fake_result]
    monkeypatch.setattr("app.services.ocr._get_local_ocr", lambda: fake_ocr)

    from app.services.ocr import ocr_image
    db = MagicMock()
    result = ocr_image(str(img), db)
    assert "测试文本" in result.text
    assert result.scores == [0.99]


def test_ocr_batch():
    results = [OcrResult(text=f"page {i}") for i in range(3)]
    with patch("app.services.ocr.ocr_image", side_effect=results):
        batch = ocr_batch(["a.jpg", "b.jpg", "c.jpg"], db=MagicMock())
    assert len(batch) == 3
    assert batch[0].text == "page 0"
    assert batch[2].text == "page 2"