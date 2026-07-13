import logging
import os
import re
import socket
import subprocess
import threading
import time
from typing import Optional
from urllib.parse import urlparse

from app.config import get_settings

logger = logging.getLogger(__name__)

_TUNNEL_URL: Optional[str] = None
_PROC: Optional[subprocess.Popen] = None
_LOCK = threading.Lock()
_MAINTENANCE_LOCK = threading.Lock()
_LOCAL_PROBE_SUPPORTED: Optional[bool] = None
_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.IGNORECASE)
_RESERVED_HOSTS = {"api.trycloudflare.com", "www.trycloudflare.com"}


def _extract_quick_tunnel_url(text: str) -> str | None:
    for match in _URL_RE.finditer(text):
        url = match.group(0).rstrip("/")
        host = url.removeprefix("https://").lower()
        if host not in _RESERVED_HOSTS:
            return url
    return None


def _read_url(stream, out: dict) -> None:
    for line in iter(stream.readline, ""):
        text = line.decode("utf-8", "ignore") if isinstance(line, bytes) else line
        logger.debug("[cloudflared] %s", text.rstrip())
        if out.get("url"):
            continue
        url = _extract_quick_tunnel_url(text)
        if url:
            out["url"] = url


def _probe_tunnel(url: str, timeout: float = 3.0) -> bool:
    import httpx

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, trust_env=False) as client:
            response = client.get(f"{url}/static/media/__smart_scribe_tunnel_probe__")
        return response.status_code in {200, 404}
    except Exception:
        return False


def _hostname_resolves(url: str) -> bool:
    hostname = urlparse(url).hostname
    if not hostname:
        return False
    try:
        socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        return True
    except OSError:
        return False


def _wait_until_reachable(url: str, timeout: float = 15.0) -> bool:
    """隧道 URL 出现在 cloudflared 输出里 ≠ Cloudflare 边缘已传播路由。
    自己 HTTP 探测直到能访问，避免 ASR 立刻去拉导致 FILE_DOWNLOAD_FAILED。
    绕过代理：探测的是 Cloudflare 公网 URL，走代理可能 SSL 出错。
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _probe_tunnel(url, timeout=min(3.0, max(0.5, deadline - time.time()))):
            logger.info("tunnel readiness check passed: %s", url)
            return True
        time.sleep(1)
    logger.warning("tunnel readiness check timed out; proceeding with provider-side verification")
    return False


def _kill_stale_cloudflared() -> None:
    """杀掉残留的 cloudflared 进程（上次后端被杀但 cloudflared 没跟着退）。"""
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", "cloudflared.exe"],
            capture_output=True, timeout=5,
        )
        if result.returncode == 0:
            logger.info("killed stale cloudflared process")
    except Exception:
        pass


def start_tunnel(port: int | None = None, timeout: float = 40.0) -> str:
    """启动 cloudflared quick tunnel，返回公网根地址。进程级单例。"""
    global _TUNNEL_URL, _PROC, _LOCAL_PROBE_SUPPORTED
    with _LOCK:
        if _TUNNEL_URL:
            return _TUNNEL_URL
        target = port or get_settings().tunnel_target_port
        # 杀掉残留的 cloudflared（上次后端被杀但子进程没跟着退）
        _kill_stale_cloudflared()
        # cloudflared 用 QUIC/HTTP2 连 Cloudflare 边缘，标准 HTTP 代理不支持 QUIC，
        # 继承 HTTPS_PROXY 会导致 cloudflared 启动后立即退出。启动时清除代理变量。
        tunnel_env = {k: v for k, v in os.environ.items() if not k.lower().endswith("_proxy") and not k.lower().endswith("_proxies")}
        out: dict = {}
        try:
            _PROC = subprocess.Popen(
                ["cloudflared", "tunnel", "--url", f"http://localhost:{target}", "--no-autoupdate"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                env=tunnel_env,
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
                _LOCAL_PROBE_SUPPORTED = _wait_until_reachable(_TUNNEL_URL)
                logger.info("cloudflared quick tunnel 就绪: %s", _TUNNEL_URL)
                return _TUNNEL_URL
            if _PROC.poll() is not None:
                raise RuntimeError("cloudflared 启动后立即退出，请检查日志")
            time.sleep(0.3)
        raise TimeoutError("等待 cloudflared 隧道域名超时")


def get_tunnel_url() -> Optional[str]:
    return _TUNNEL_URL


def reset_tunnel() -> None:
    global _TUNNEL_URL, _PROC, _LOCAL_PROBE_SUPPORTED
    with _LOCK:
        if _PROC and _PROC.poll() is None:
            try:
                _PROC.terminate()
                _PROC.wait(timeout=3)
            except Exception:
                try:
                    _PROC.kill()
                except Exception:
                    pass
        _PROC = None
        _TUNNEL_URL = None
        _LOCAL_PROBE_SUPPORTED = None


def ensure_public_base_url() -> Optional[str]:
    """Return a usable public URL, rebuilding a stale auto tunnel before ASR submission."""
    global _LOCAL_PROBE_SUPPORTED

    settings = get_settings()
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    if settings.tunnel != "auto":
        return None

    with _MAINTENANCE_LOCK:
        current = get_tunnel_url()
        if not current:
            return start_tunnel().rstrip("/")

        process_alive = _PROC is not None and _PROC.poll() is None
        dns_alive = _hostname_resolves(current)
        if not process_alive or not dns_alive:
            logger.warning(
                "ASR tunnel preflight found a stale tunnel (process_alive=%s, dns_alive=%s); rebuilding",
                process_alive,
                dns_alive,
            )
            reset_tunnel()
            return start_tunnel().rstrip("/")

        # Some networks cannot reach trycloudflare directly even though DashScope can.
        # Only treat an HTTP probe failure as definitive after this process has
        # previously confirmed that direct probing works.
        if _LOCAL_PROBE_SUPPORTED is not False:
            reachable = _probe_tunnel(current)
            if reachable:
                _LOCAL_PROBE_SUPPORTED = True
            elif _LOCAL_PROBE_SUPPORTED is True:
                logger.warning("ASR tunnel preflight failed after prior success; rebuilding")
                reset_tunnel()
                return start_tunnel().rstrip("/")
            else:
                _LOCAL_PROBE_SUPPORTED = False
                logger.info(
                    "ASR tunnel HTTPS preflight is unavailable on this network; "
                    "keeping DNS-valid tunnel and relying on provider-side retry"
                )

        return current.rstrip("/")


def resolve_public_base_url() -> Optional[str]:
    """已配置就走配置；否则在 tunnel=auto 时自动起隧道。"""
    settings = get_settings()
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    if settings.tunnel == "auto":
        return start_tunnel().rstrip("/")
    return None
