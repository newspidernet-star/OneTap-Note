import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

from app.services.storage import session_storage_dir


class MaterialSpec:
    def __init__(self, file_path: str, media_type: str, original_url: str):
        self.file_path = file_path
        self.media_type = media_type
        self.original_url = original_url


# 抖音移动端 User-Agent，用于访问 iesdouyin.com/share/video/ 的 SSR 页面
_DOUYIN_MOBILE_UA = (
    "com.ss.android.ugc.aweme/330601 "
    "(Linux; U; Android 10; zh_CN; Pixel 4)"
)


def _extract_url(text: str) -> str:
    """从用户粘贴的分享文本中提取第一个 http/https URL。"""
    text = text.strip()
    # 匹配 http:// 或 https:// 开头的 URL，直到空白或常见中文标点
    match = re.search(r"https?://[^\s\u3000\uff0c\u3002\uff1b\uff01\uff1f\u201c\u201d\u300a\u300b\uff08\uff09]+", text)
    if match:
        return match.group(0)
    return text


def detect_platform(raw: str) -> str:
    url = _extract_url(raw)
    host = urlparse(url).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "bilibili.com" in host or "b23.tv" in host:
        return "bilibili"
    if "iesdouyin.com/share/article" in url or "/note/" in url:
        return "douyin_image"
    if "douyin.com" in host or "iesdouyin.com" in host:
        return "douyin_video"
    ext = Path(urlparse(url).path).suffix.lower()
    if ext in {".mp4", ".mkv", ".webm", ".mp3", ".wav", ".m4a", ".jpg", ".jpeg", ".png"}:
        return "direct"
    return "unknown"


def _find_video_url_in_router(data: dict) -> str | None:
    """在 window._ROUTER_DATA 中递归查找视频播放地址。"""
    stack = [data]
    while stack:
        obj = stack.pop()
        if isinstance(obj, dict):
            play_addr = obj.get("play_addr")
            if isinstance(play_addr, dict):
                url_list = play_addr.get("url_list", [])
                if url_list:
                    return url_list[0]
            for v in obj.values():
                stack.append(v)
        elif isinstance(obj, list):
            stack.extend(obj)
    return None


def download_bilibili_video(raw: str, session_id: int) -> str:
    """通过 Bilibili 公开 API 下载视频（无需 cookie）。

    流程：
    1. 从链接中提取 BV 号
    2. 用 view API 获取 cid
    3. 用 playurl API 获取视频直链
    4. 下载到会话目录
    """
    url = _extract_url(raw)
    d = session_storage_dir(session_id)
    d.mkdir(parents=True, exist_ok=True)

    m = re.search(r"(BV[a-zA-Z0-9]+)", url)
    if not m:
        raise RuntimeError(f"无法从链接中提取 Bilibili BV 号: {url}")
    bvid = m.group(1)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com/",
    }

    try:
        info_resp = requests.get(
            f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
            headers=headers, timeout=30,
        )
        info_resp.raise_for_status()
        info = info_resp.json()
    except Exception as e:
        raise RuntimeError(f"获取 Bilibili 视频信息失败: {e}") from e
    if info.get("code") != 0:
        raise RuntimeError(f"Bilibili API 返回错误: {info.get('message')}")

    cid = info["data"]["cid"]
    title = info["data"].get("title", bvid)

    try:
        play_resp = requests.get(
            f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=80&fnval=1&fourk=1",
            headers=headers, timeout=30,
        )
        play_resp.raise_for_status()
        play = play_resp.json()
    except Exception as e:
        raise RuntimeError(f"获取 Bilibili 播放地址失败: {e}") from e
    if play.get("code") != 0:
        raise RuntimeError(f"Bilibili playurl API 返回错误: {play.get('message')}")

    durls = play["data"].get("durl")
    if not durls:
        raise RuntimeError("Bilibili playurl 返回空播放列表")

    video_url = durls[0]["url"]

    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:80]
    ext = ".mp4"
    dest = d / f"{safe_title}{ext}"

    try:
        video_resp = requests.get(
            video_url,
            headers={**headers, "Accept": "*/*"},
            allow_redirects=True, timeout=120,
        )
        video_resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"下载 Bilibili 视频失败: {e}") from e

    dest.write_bytes(video_resp.content)
    return str(dest)


def download_douyin_video(raw: str, session_id: int) -> str:
    """通过抖音移动端分享页 SSR 数据下载视频（无需 cookie）。

    流程：
    1. 访问短链/分享链，跟随 302 到 iesdouyin.com/share/video/{id}/
    2. 用移动端 UA 获取 HTML，提取 window._ROUTER_DATA
    3. 从视频信息中获取 play_addr.url_list[0]，并将 /playwm/ 替换为 /play/
    4. 下载视频到会话目录
    """
    url = _extract_url(raw)
    d = session_storage_dir(session_id)
    d.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": _DOUYIN_MOBILE_UA}
    try:
        resp = requests.get(url, headers=headers, allow_redirects=True, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"访问抖音分享页失败: {e}") from e

    # 兼容多种 _ROUTER_DATA 写法：带 </script> 结尾或行内结束
    match = re.search(r"window\._ROUTER_DATA\s*=\s*({.*?})</script>", resp.text, re.DOTALL)
    if not match:
        match = re.search(r"window\._ROUTER_DATA\s*=\s*({.*})", resp.text, re.DOTALL)
    if not match:
        raise RuntimeError("无法从抖音分享页提取视频数据（未找到 _ROUTER_DATA）")

    try:
        router_data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"解析抖音页面数据失败: {e}") from e

    video_url = _find_video_url_in_router(router_data)
    if not video_url:
        raise RuntimeError("未在抖音页面数据中找到视频播放地址")

    # 去水印：playwm -> play
    video_url = video_url.replace("/playwm/", "/play/")

    try:
        video_resp = requests.get(video_url, headers=headers, allow_redirects=True, timeout=120)
        video_resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"下载抖音视频失败: {e}") from e

    ext = ".mp4"
    content_type = video_resp.headers.get("content-type", "")
    if "video/" in content_type:
        ext = "." + content_type.split("/")[-1].split(";")[0].strip()
    dest = d / f"douyin_video{ext}"
    dest.write_bytes(video_resp.content)
    return str(dest)


def download_video(url: str, session_id: int, cookie_path: str | None = None) -> str:
    import yt_dlp

    d = session_storage_dir(session_id)
    outtmpl = str(d / "%(title)s.%(ext)s")
    ydl_opts: dict = {"outtmpl": outtmpl, "format": "best"}
    if cookie_path and Path(cookie_path).exists():
        ydl_opts["cookiefile"] = cookie_path
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


def download_images(url: str, session_id: int) -> list[str]:
    from playwright.sync_api import sync_playwright

    d = session_storage_dir(session_id)
    paths = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        images = page.query_selector_all("img")
        for i, img in enumerate(images):
            src = img.get_attribute("src")
            if not src:
                continue
            if src.startswith("//"):
                src = "https:" + src
            if not src.startswith("http"):
                continue
            ext = Path(urlparse(src).path).suffix or ".jpg"
            dest = d / f"image_{i:03d}{ext}"
            try:
                resp = page.request.get(src)
                dest.write_bytes(resp.body())
                paths.append(str(dest))
            except Exception:
                continue
        browser.close()
    return paths


def download(raw: str, session_id: int, cookie_path: str | None = None) -> list[MaterialSpec]:
    url = _extract_url(raw)
    platform = detect_platform(url)
    if platform == "douyin_video":
        # 优先使用移动端分享页免 cookie 下载；失败且提供 cookie 时回退 yt-dlp
        try:
            path = download_douyin_video(raw, session_id)
        except Exception as e:
            if cookie_path and Path(cookie_path).exists():
                path = download_video(url, session_id, cookie_path=cookie_path)
            else:
                raise
        media_type = "video"
        if Path(path).suffix.lower() in {".mp3", ".m4a", ".wav"}:
            media_type = "audio"
        return [MaterialSpec(path, media_type, url)]
    if platform == "bilibili":
        path = download_bilibili_video(raw, session_id)
        media_type = "video"
        if Path(path).suffix.lower() in {".mp3", ".m4a", ".wav"}:
            media_type = "audio"
        return [MaterialSpec(path, media_type, url)]
    elif platform == "youtube":
        path = download_video(url, session_id, cookie_path=cookie_path)
        media_type = "video"
        if Path(path).suffix.lower() in {".mp3", ".m4a", ".wav"}:
            media_type = "audio"
        return [MaterialSpec(path, media_type, url)]
    if platform == "douyin_image":
        paths = download_images(url, session_id)
        return [MaterialSpec(p, "image", url) for p in paths]
    if platform == "direct":
        import urllib.request
        d = session_storage_dir(session_id)
        filename = Path(urlparse(url).path).name or "download.bin"
        dest = d / filename
        with urllib.request.urlopen(url) as resp:
            dest.write_bytes(resp.read())
        media_type = "video" if dest.suffix in {".mp4", ".mkv", ".webm"} else "audio" if dest.suffix in {".mp3", ".wav", ".m4a"} else "image"
        return [MaterialSpec(str(dest), media_type, url)]
    raise ValueError(f"不支持的平台: {raw}")
