from app.services.downloader import detect_platform


def test_detect_youtube():
    assert detect_platform("https://www.youtube.com/watch?v=abc") == "youtube"
    assert detect_platform("https://youtu.be/abc") == "youtube"


def test_detect_bilibili():
    assert detect_platform("https://www.bilibili.com/video/BV1xx") == "bilibili"
    assert detect_platform("https://b23.tv/abc") == "bilibili"


def test_detect_douyin():
    assert detect_platform("https://www.douyin.com/video/123") == "douyin_video"


def test_detect_douyin_image_note():
    assert detect_platform("https://www.douyin.com/note/123456") == "douyin_image"


def test_detect_douyin_image_article():
    assert detect_platform("https://www.iesdouyin.com/share/article/123456") == "douyin_image"


def test_detect_direct():
    assert detect_platform("https://example.com/file.mp4") == "direct"
    assert detect_platform("https://example.com/file.mp3") == "direct"


def test_detect_unknown():
    assert detect_platform("https://example.com/page") == "unknown"
