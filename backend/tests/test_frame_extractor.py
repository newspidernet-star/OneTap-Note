from pathlib import Path

import ffmpeg

from app.services.frame_extractor import dedup_frames, extract_and_dedup, extract_frames


def _make_test_video(path: str, duration: float = 9.0):
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    (
        ffmpeg.input(f"color=c=red:s=64x64:d={duration}", f="lavfi")
        .output(str(out), vcodec="libx264", pix_fmt="yuv420p", r=10)
        .overwrite_output()
        .run(quiet=True)
    )


def test_extract_frames(tmp_path):
    video = str(tmp_path / "test.mp4")
    _make_test_video(video, duration=9.0)
    frames = extract_frames(video, str(tmp_path / "frames"), interval=3.0)
    assert len(frames) >= 2
    for p in frames:
        assert Path(p).exists()


def test_dedup_frames_identical(tmp_path):
    video = str(tmp_path / "test.mp4")
    _make_test_video(video, duration=6.0)
    frames = extract_frames(video, str(tmp_path / "frames"), interval=2.0)
    deduped = dedup_frames(frames, threshold=0.95)
    assert len(deduped) == 1


def test_extract_and_dedup(tmp_path):
    video = str(tmp_path / "test.mp4")
    _make_test_video(video, duration=9.0)
    result = extract_and_dedup(video, str(tmp_path / "frames"), interval=3.0)
    assert len(result) >= 1
    for p in result:
        assert Path(p).exists()


def test_dedup_frames_empty():
    assert dedup_frames([]) == []