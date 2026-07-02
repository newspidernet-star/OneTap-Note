import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.media import router as media_router
from app.api.settings import router as settings_router
from app.api.speech import router as speech_router
from app.api.summary import router as summary_router
from app.config import get_settings
from app.database import init_db


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)

    init_db()

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
    if settings.tunnel_mode == "auto" and not settings.public_base_url:

        class TunnelGuardMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                # 带有 Cloudflare 标记头说明流量来自隧道
                if request.headers.get("CF-RAY") and not request.url.path.startswith("/static"):
                    return Response("tunnel mode: only /static is exposed", status_code=403)
                return await call_next(request)

        app.add_middleware(TunnelGuardMiddleware)

    return app


app = create_app()