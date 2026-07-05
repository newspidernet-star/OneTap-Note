import logging
import subprocess
from pathlib import Path

import cv2
import ffmpeg
import numpy as np
from PIL import Image

FPS = 2
PREVIEW_WIDTH = 480
SIMILARITY_THRESHOLD = 0.97  # 0.95→0.97：让"往幻灯片上加文字"不触发场景切换，累积态留在同组
MIN_TEXT_AREA = 0.005
MAX_KEYFRAMES = 30  # 最多保留 N 个关键帧送 OCR，避免长视频几百帧把云端 OCR 打爆
SUBTITLE_BOTTOM_RATIO = 0.20  # 字幕检测区域：底部 20%
SUBTITLE_SIM_THRESHOLD = 0.85  # 底部相似度低于此值 → 判定该组底部有字幕（文字在变）

_log = logging.getLogger("smart_scribe")


def text_score(bgr: np.ndarray, exclude_bottom_ratio: float = 0.0) -> float:
    """计算画面文字密度。exclude_bottom_ratio > 0 时裁掉底部（字幕区），避免字幕干扰得分。"""
    try:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    except Exception:
        return 0.0
    h, w = gray.shape
    # 排除底部字幕区：字幕和语音转写重复，是噪音
    if exclude_bottom_ratio > 0:
        crop_h = int(h * (1 - exclude_bottom_ratio))
        gray = gray[:crop_h, :]
        h = crop_h
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
        # stderr=DEVNULL：ffmpeg 会往 stderr 写大量进度信息，如果用 PIPE 但不读，
        # 管道缓冲区满后 ffmpeg 会阻塞写 stderr → stdout 也停 → 死锁（10分钟卡死根因）
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
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
    """提取完整原图，不裁剪——字幕排除只在选帧逻辑里做，保存的帧保持完整不丢信息。"""
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


def _detect_subtitle_in_group(group: list[tuple[float, np.ndarray]]) -> bool:
    """差分字幕检测：同一场景组内，如果首尾帧整体相似但底部区域不相似，
    说明底部有'位置固定但内容在变'的文字 = 字幕。

    对"顶部标题 + 长间隔后新标题"不会误判（它们会被分到不同组）。
    对"上部累积文字"也不会误判（首尾底部相似度高，不触发字幕判定）。
    """
    if len(group) < 3:
        return False
    first = group[0][1]
    last = group[-1][1]
    h = first.shape[0]
    crop = int(h * (1 - SUBTITLE_BOTTOM_RATIO))
    overall_sim = frame_similarity(first, last)
    bottom_sim = frame_similarity(first[crop:, :], last[crop:, :])
    # 整体相似（同一场景）但底部不相似（底部文字在变）→ 字幕
    is_subtitle = overall_sim > 0.90 and bottom_sim < SUBTITLE_SIM_THRESHOLD
    if is_subtitle:
        _log.info(f"[FRAMES] subtitle detected in group: overall_sim={overall_sim:.3f}, bottom_sim={bottom_sim:.3f}")
    return is_subtitle


def extract_keyframes(video_path: str, output_dir: str) -> list[tuple[float, str]]:
    """增量幻灯片重建：不是每帧 OCR，而是模拟"看 PPT 翻页"的过程。

    流程：
    1. FFmpeg 抽帧（自适应 fps）
    2. 按帧差异分组（同一幻灯片 = 同一组，加文字不触发切换）
    3. 差分字幕检测（底部固定位置文字在变 = 字幕，排除）
    4. 每组只 OCR 最后一帧（累积态最完整）→ 大幅减少 OCR 调用
    5. 长视频最多 30 个关键帧
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    frames = _stream_frames(video_path)
    if not frames:
        return []

    # --- 阶段 1：按场景分组（增量检测）---
    groups: list[list[tuple[float, np.ndarray]]] = []
    current_group = [frames[0]]
    for i in range(1, len(frames)):
        sim = frame_similarity(current_group[-1][1], frames[i][1])
        if sim > SIMILARITY_THRESHOLD:
            # 画面稳定（同一幻灯片 + 可能加了文字）→ 继续累积
            current_group.append(frames[i])
        else:
            # 画面大幅变化 → 翻页，保存当前组，开始新组
            groups.append(current_group)
            current_group = [frames[i]]
    groups.append(current_group)
    _log.info(f"[FRAMES] {len(groups)} slide groups detected from {len(frames)} sampled frames")

    # --- 阶段 2：每组选最优帧（字幕检测 + 取累积最完整帧）---
    candidates: list[tuple[float, float]] = []
    subtitle_groups = 0
    for gi, group in enumerate(groups):
        if len(group) < 1:
            continue
        # 差分字幕检测
        has_subtitle = _detect_subtitle_in_group(group)
        if has_subtitle:
            subtitle_groups += 1
            # 有字幕：排除底部算 score，找上部文字最多的帧
            exclude_ratio = SUBTITLE_BOTTOM_RATIO
            best_ts = group[0][0]
            best_score = -1.0
            for ts, bgr in group:
                try:
                    s = text_score(bgr, exclude_bottom_ratio=exclude_ratio)
                except Exception:
                    continue
                if s > best_score:
                    best_score = s
                    best_ts = ts
        else:
            # 无字幕：取最后一帧 = 累积态最完整（5s 加第一点 → 15s 三点全 → 取 15s 那帧）
            best_ts = group[-1][0]
            try:
                best_score = text_score(group[-1][1])
            except Exception:
                best_score = 0.0
        if best_score > MIN_TEXT_AREA:
            candidates.append((best_ts, best_score))
        if (gi + 1) % 10 == 0:
            _log.info(f"[FRAMES] ... processed {gi+1}/{len(groups)} slide groups")

    _log.info(f"[FRAMES] {len(groups)} slides ({subtitle_groups} with subtitle), {len(candidates)} with text, from {len(frames)} frames")

    # 结尾帧兜底
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe["format"]["duration"])
        last_sampled_ts = frames[-1][0] if frames else 0.0
        if duration - last_sampled_ts > 0.2:
            end_ts = duration * 0.98
            if not candidates or abs(candidates[-1][0] - end_ts) > 0.2:
                candidates.append((end_ts, 1.0))
    except Exception:
        pass

    # 长视频最多 MAX_KEYFRAMES 帧
    if len(candidates) > MAX_KEYFRAMES:
        _log.info(f"[FRAMES] {len(candidates)} > {MAX_KEYFRAMES} cap, keeping top {MAX_KEYFRAMES}")
        candidates.sort(key=lambda x: x[1], reverse=True)
        candidates = candidates[:MAX_KEYFRAMES]
        candidates.sort(key=lambda x: x[0])

    _log.info(f"[FRAMES] {len(candidates)} keyframes selected, extracting full frames...")

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
