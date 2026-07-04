import logging
import re
import subprocess
import threading
import time
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

_TUNNEL_URL: Optional[str] = None
_PROC: Optional[subprocess.Popen] = None
_LOCK = threading.Lock()
_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.IGNORECASE)


def _read_url(stream, out: dict) -> None:
    for line in iter(stream.readline, ""):
        text = line.decode("utf-8", "ignore") if isinstance(line, bytes) else line
        logger.info("[cloudflared] %s", text.rstrip())
        if out.get("url"):
            continue
        m = _URL_RE.search(text)
        if m:
            out["url"] = m.group(0)


def _wait_until_reachable(url: str, timeout: float = 15.0) -> None:
    """隧道 URL 出现在 cloudflared 输出里 ≠ Cloudflare 边缘已传播路由。
    自己 HTTP 探测直到能访问，避免 ASR 立刻去拉导致 FILE_DOWNLOAD_FAILED。
    """
    import httpx
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            r = httpx.get(f"{url}/api/health", timeout=5, follow_redirects=True)
            if r.status_code == 200:
                logger.info("tunnel readiness check passed: %s", url)
                return
        except Exception as e:
            last_err = e
        time.sleep(1)
    logger.warning("tunnel readiness check timed out (last err: %s); proceeding anyway", last_err)


def start_tunnel(port: int | None = None, timeout: float = 40.0) -> str:
    """启动 cloudflared quick tunnel，返回公网根地址。进程级单例。"""
    global _TUNNEL_URL, _PROC
    with _LOCK:
        if _TUNNEL_URL:
            return _TUNNEL_URL
        target = port or get_settings().tunnel_target_port
        out: dict = {}
        try:
            _PROC = subprocess.Popen(
                ["cloudflared", "tunnel", "--url", f"http://localhost:{target}", "--no-autoupdate"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "未找到 cloudflared 可执行文件。请安装 cloudflared "
                "(https://github.com/cloudflare/cloudflared/releases) 或自行配置 SMART_SCRIBE_PUBLIC_BASE_URL。"
            )
        reader = threading.Thread(target=_read_url, args=(_PROC.stdout, out), daemon=True)
        reader.start()
        deadline = time.time() + timeout
        while time.time() < deadline:
            if out.get("url"):
                _TUNNEL_URL = out["url"]
                logger.info("cloudflared quick tunnel URL obtained: %s", _TUNNEL_URL)
                logger.info("waiting for tunnel to become reachable...")
                _wait_until_reachable(_TUNNEL_URL)
                logger.info("cloudflared quick tunnel 就绪: %s", _TUNNEL_URL)
                return _TUNNEL_URL
            if _PROC.poll() is not None:
                raise RuntimeError("cloudflared 启动后立即退出，请检查日志")
            time.sleep(0.3)
        raise TimeoutError("等待 cloudflared 隧道域名超时")


def get_tunnel_url() -> Optional[str]:
    return _TUNNEL_URL


def resolve_public_base_url() -> Optional[str]:
    """已配置就走配置；否则在 tunnel=auto 时自动起隧道。"""
    settings = get_settings()
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    if settings.tunnel == "auto":
        return start_tunnel().rstrip("/")
    return None