from pathlib import Path

import ffmpeg

from app.services.frame_extractor import (
    COVERAGE_KEYFRAMES,
    MAX_KEYFRAMES,
    _choose_frame_strategy,
    _select_candidates,
    dedup_frames,
    extract_and_dedup,
    extract_frames,
)


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


def test_choose_frame_strategy_switches_to_coverage_for_dense_scenes():
    strategy, cap, groups_per_minute = _choose_frame_strategy(
        groups_count=120,
        candidates_count=80,
        duration=300,
    )
    assert strategy == "coverage"
    assert cap == COVERAGE_KEYFRAMES
    assert groups_per_minute == 24


def test_choose_frame_strategy_keeps_conservative_for_sparse_scenes():
    strategy, cap, _ = _choose_frame_strategy(
        groups_count=8,
        candidates_count=8,
        duration=300,
    )
    assert strategy == "conservative"
    assert cap == MAX_KEYFRAMES


def test_select_candidates_coverage_keeps_time_buckets():
    candidates = [(float(i), float(i % 7) / 10.0 + 0.1) for i in range(0, 120, 3)]
    selected = _select_candidates(candidates, cap=10, strategy="coverage", bucket_seconds=12)
    selected_buckets = {int(ts // 12) for ts, _ in selected}
    assert len(selected) == 10
    assert len(selected_buckets) >= 8
