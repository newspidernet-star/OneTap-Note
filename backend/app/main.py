import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.media import router as media_router
from app.api.settings import router as settings_router
from app.api.speech import router as speech_router
from app.api.summary import router as summary_router
from app.config import get_settings
from app.database import init_db
from app.services.sweeper import start_sweeper


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # 降噪：httpx 请求日志、jieba 调试、uvicorn access log 太吵，淹没了处理进度
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("jieba").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)

    init_db()
    # ephemeral=true 时启动后台清扫线程（本地默认 false，不扫）
    start_sweeper()

    app = FastAPI(title="Smart Scribe", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    app.include_router(settings_router)
    app.include_router(media_router)
    app.include_router(speech_router)
    app.include_router(summary_router)

    app.mount("/static/media", StaticFiles(directory=str(settings.storage_dir.resolve())), name="media")

    # 自动隧道模式下，只允许隧道访问 /static 媒体路径，屏蔽 /api 等接口
    if settings.tunnel == "auto" and not settings.public_base_url:

        class TunnelGuardMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                # 带有 Cloudflare 标记头说明流量来自隧道
                if request.headers.get("CF-RAY") and not request.url.path.startswith("/static"):
                    return Response("tunnel mode: only /static is exposed", status_code=403)
                return await call_next(request)

        app.add_middleware(TunnelGuardMiddleware)

    # 一键启动 / 生产模式：若前端已构建，由后端直接托管（SPA fallback）。
    # 开发模式仍用 npm run dev（:5173 代理到 :8000）。
    frontend_dist = Path(settings.frontend_dist_dir) if settings.frontend_dist_dir else (Path(__file__).resolve().parents[2] / "frontend" / "dist")
    if frontend_dist.exists():
        @app.get("/{full_path:path}")
        async def _spa(full_path: str):
            candidate = frontend_dist / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(frontend_dist / "index.html")

    return app


app = create_app()