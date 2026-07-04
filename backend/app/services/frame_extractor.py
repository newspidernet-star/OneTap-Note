import logging
import subprocess
from pathlib import Path

import cv2
import ffmpeg
import numpy as np
from PIL import Image

FPS = 2
PREVIEW_WIDTH = 480
SIMILARITY_THRESHOLD = 0.95
MIN_TEXT_AREA = 0.005
MAX_KEYFRAMES = 30  # 最多保留 N 个关键帧送 OCR，避免长视频几百帧把云端 OCR 打爆

_log = logging.getLogger("smart_scribe")


def text_score(bgr: np.ndarray) -> float:
    try:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    except Exception:
        return 0.0
    h, w = gray.shape
    try:
        gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    except Exception:
        pass
    try:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        white = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
        black = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
        stroke = cv2.max(white, black)
        _, bw = cv2.threshold(stroke, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)))
        connected = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (12, 2)))
    except Exception:
        return 0.0
    try:
        num, labels, stats, _ = cv2.connectedComponentsWithStats(connected, 8)
    except Exception:
        return 0.0
    score = 0
    for x, y, cw, ch, area in stats[1:]:
        if ch < h * 0.012 or ch > h * 0.20:
            continue
        if cw < w * 0.015:
            continue
        aspect = cw / max(ch, 1)
        if aspect < 1.2 or aspect > 80:
            continue
        fill = area / max(cw * ch, 1)
        if fill < 0.03 or fill > 0.75:
            continue
        score += cw * ch
    return score / (w * h)


def frame_similarity(a: np.ndarray, b: np.ndarray) -> float:
    try:
        a_g = cv2.resize(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), (96, 54))
        b_g = cv2.resize(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), (96, 54))
        a_g = cv2.GaussianBlur(a_g, (5, 5), 0)
        b_g = cv2.GaussianBlur(b_g, (5, 5), 0)
        return 1.0 - float(cv2.absdiff(a_g, b_g).mean()) / 255.0
    except Exception:
        return 0.0


def _stream_frames(video_path: str) -> list[tuple[float, np.ndarray]]:
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe["format"]["duration"])
        streams = [s for s in probe.get("streams", []) if s["codec_type"] == "video"]
        if not streams:
            _log.warning("No video stream in %s", video_path)
            return []
        original_w = int(streams[0]["width"])
        original_h = int(streams[0]["height"])
        height = int(original_h * PREVIEW_WIDTH / original_w)

        # 短视频逐帧看，避免结尾画面/快速字幕被漏掉；长视频降采样省资源
        r_frame_rate = streams[0].get("r_frame_rate", "30/1")
        try:
            num, den = r_frame_rate.split("/")
            native_fps = float(num) / float(den)
        except Exception:
            native_fps = 30.0
        if duration <= 3:
            sample_fps = min(native_fps, 30.0)
        elif duration <= 10:
            sample_fps = 5.0
        elif duration <= 60:
            sample_fps = 2.0   # 1-10 分钟：2fps
        elif duration <= 300:
            sample_fps = 1.0   # 5-10 分钟：1fps
        else:
            sample_fps = 0.5   # >5 分钟：0.5fps，避免帧数爆炸
    except Exception:
        _log.warning("ffprobe failed for %s", video_path)
        return []

    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps={sample_fps},scale={PREVIEW_WIDTH}:-1",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-an", "-sn", "pipe:1",
    ]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        _log.warning("ffmpeg pipe failed for %s", video_path)
        return []

    frames = []
    idx = 0
    raw_size = PREVIEW_WIDTH * height * 3
    expected = int(duration * sample_fps) if duration else 0
    _log.info(f"[FRAMES] streaming {video_path}: duration={duration:.1f}s, sample_fps={sample_fps}, expect ~{expected} frames")
    while True:
        try:
            raw = proc.stdout.read(raw_size)
        except Exception:
            break
        if len(raw) < raw_size:
            break
        try:
            bgr = np.frombuffer(raw, dtype=np.uint8).reshape((height, PREVIEW_WIDTH, 3))
        except Exception:
            continue
        ts = min(idx / sample_fps, duration)
        frames.append((ts, bgr))
        idx += 1
        if idx % 100 == 0:
            _log.info(f"[FRAMES] ... {idx} frames read ({ts:.1f}s/{duration:.1f}s)")

    try:
        proc.terminate()
    except Exception:
        pass
    return frames


def _extract_full_frame(video_path: str, timestamp: float, output_dir: str, filename: str) -> str:
    dest = str(Path(output_dir) / filename)
    try:
        (
            ffmpeg.input(video_path, ss=timestamp)
            .output(dest, vframes=1, format="image2", vcodec="mjpeg", qscale=2)
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error:
        return ""
    return dest if Path(dest).exists() else ""


def extract_keyframes(video_path: str, output_dir: str) -> list[tuple[float, str]]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    frames = _stream_frames(video_path)
    if not frames:
        return []

    candidates: list[tuple[float, float]] = []
    try:
        current_best_score = text_score(frames[0][1])
    except Exception:
        current_best_score = 0.0
    current_best_ts = frames[0][0]
    prev = frames[0][1]

    for ts, bgr in frames[1:]:
        try:
            score = text_score(bgr)
            sim = frame_similarity(prev, bgr)
        except Exception:
            prev = bgr
            continue
        if sim > SIMILARITY_THRESHOLD:
            if score > current_best_score:
                current_best_score = score
                current_best_ts = ts
        else:
            if current_best_score > MIN_TEXT_AREA:
                candidates.append((current_best_ts, current_best_score))
            current_best_score = score
            current_best_ts = ts
        prev = bgr

    if current_best_score > MIN_TEXT_AREA:
        candidates.append((current_best_ts, current_best_score))

    # 很多短视频的文字/结尾画面出现在最后一帧；均匀采样可能漏掉它，
    # 所以显式把临近结尾的一帧也加进候选。
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe["format"]["duration"])
        last_sampled_ts = frames[-1][0] if frames else 0.0
        if duration - last_sampled_ts > 0.2:
            end_ts = duration * 0.98
            # 避免和最后一个候选重复
            if not candidates or abs(candidates[-1][0] - end_ts) > 0.2:
                candidates.append((end_ts, 1.0))
    except Exception:
        pass

    # 长视频候选太多时，只保留文字得分最高的 N 个，按时间重排
    if len(candidates) > MAX_KEYFRAMES:
        _log.info(f"[FRAMES] {len(candidates)} candidates > {MAX_KEYFRAMES} cap, keeping top {MAX_KEYFRAMES} by text_score")
        candidates.sort(key=lambda x: x[1], reverse=True)
        candidates = candidates[:MAX_KEYFRAMES]
        candidates.sort(key=lambda x: x[0])

    _log.info(f"[FRAMES] {len(candidates)} keyframes selected from {len(frames)} sampled frames")

    paths = []
    for i, (ts, _) in enumerate(candidates):
        filename = f"frame_{i:04d}.jpg"
        path = _extract_full_frame(video_path, ts, output_dir, filename)
        if path:
            paths.append((ts, path))
    return paths


# --- Legacy API kept for tests that import these names ---
def extract_frames(video_path: str, output_dir: str, interval: float = 3.0) -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    probe = ffmpeg.probe(video_path)
    duration = float(probe["format"]["duration"])
    frame_times = np.arange(0, duration, interval)
    paths = []
    for i, t in enumerate(frame_times):
        dest = str(out / f"frame_{i:04d}.jpg")
        try:
            (
                ffmpeg.input(video_path, ss=float(t))
                .output(dest, vframes=1, format="image2", vcodec="mjpeg", qscale=2)
                .overwrite_output()
                .run(quiet=True)
            )
            paths.append(dest)
        except ffmpeg.Error:
            continue
    return paths


def _load_gray(path: str) -> np.ndarray:
    img = Image.open(path).convert("L").resize((256, 256))
    return np.asarray(img, dtype=np.float32) / 255.0


def _similarity(a: str, b: str) -> float:
    ga, gb = _load_gray(a), _load_gray(b)
    diff = np.abs(ga - gb).mean()
    return 1.0 - float(diff)


def dedup_frames(frame_paths: list[str], threshold: float = 0.95) -> list[str]:
    if not frame_paths:
        return []
    kept = [frame_paths[0]]
    for p in frame_paths[1:]:
        if _similarity(kept[-1], p) < threshold:
            kept.append(p)
    return kept


def extract_and_dedup(video_path: str, output_dir: str, interval: float = 3.0) -> list[str]:
    frames = extract_frames(video_path, output_dir, interval)
    return dedup_frames(frames)
