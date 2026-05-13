from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pcad.agent.conversation_service import ConversationService
from pcad.config import Settings
from pcad.logging_utils import configure_logging

from .rate_limit import ip_rate_limiter
from .routes import router
from .sessions import SessionMiddleware


STATIC_DIR = Path(__file__).resolve().parent / "static"
RENDERED_DIR = Path("data/rendered")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Compose the FastAPI app for the public demo."""
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level, color=str(settings.log_color).lower())
    app = FastAPI(title=settings.app_title)
    app.state.settings = settings
    app.state.conversation_service = ConversationService(settings)
    app.add_middleware(SessionMiddleware, settings=settings)

    @app.middleware("http")
    async def rate_limit_api(request: Request, call_next: Any) -> Response:
        if request.url.path.startswith("/api/"):
            forwarded_for = request.headers.get("x-forwarded-for", "")
            client_ip = forwarded_for.split(",")[0].strip() or (request.client.host if request.client else "unknown")
            if not ip_rate_limiter.allow(
                f"ip:{client_ip}",
                limit=settings.rate_limit_per_ip_per_minute,
                window_seconds=60,
            ):
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=status.HTTP_429_TOO_MANY_REQUESTS)
        return await call_next(request)

    app.include_router(router, prefix="/api")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    if RENDERED_DIR.exists():
        app.mount("/rendered", StaticFiles(directory=RENDERED_DIR), name="rendered")

    @app.get("/")
    def landing() -> FileResponse:
        return FileResponse(STATIC_DIR / "landing" / "index.html")

    @app.get("/demo")
    @app.get("/demo/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
