from io import BytesIO
from fastapi import UploadFile

from app.services.storage import classify_media, save_upload


def test_classify_video():
    assert classify_media("lecture.mp4") == "video"
    assert classify_media("x.mkv") == "video"
    assert classify_media("x.txt", "video/mp4") == "video"


def test_classify_audio():
    assert classify_media("voice.m4a") == "audio"
    assert classify_media("note.mp3") == "audio"


def test_classify_image():
    assert classify_media("slide.png") == "image"
    assert classify_media("pic.jpeg") == "image"


def test_classify_unknown():
    assert classify_media("data.csv") == "unknown"


def test_save_upload(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.storage.get_settings", lambda: type("S", (), {"storage_dir": tmp_path})())
    content = b"fake video data"
    file = UploadFile(filename="test.mp4", file=BytesIO(content))
    path = save_upload(file, 1)
    assert "test.mp4" in path
    with open(path, "rb") as f:
        assert f.read() == content
