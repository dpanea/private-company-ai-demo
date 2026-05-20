from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from company_ai.agent.conversation_service import ConversationService
from company_ai.config import Settings
from company_ai.db import close_pools, connect_dict
from company_ai.logging_utils import configure_logging

from .rate_limit import ip_rate_limiter
from .routes import router
from .sessions import SessionMiddleware, periodic_session_cleanup


logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"
RENDERED_DIR = Path("data/rendered")
TRUSTED_PROXY_HOSTS = {"127.0.0.1", "::1", "localhost"}


def create_app(settings: Settings | None = None) -> FastAPI:
    """Compose the FastAPI app for the public demo."""
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level, color=settings.log_color)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        _assert_embedding_dimensions(settings)
        cleanup_task = asyncio.create_task(periodic_session_cleanup(settings))
        try:
            yield
        finally:
            cleanup_task.cancel()
            try:
                await cleanup_task
            except (asyncio.CancelledError, Exception):  # pragma: no cover
                pass
            try:
                app.state.conversation_service.llm_client.close()  # type: ignore[attr-defined]
            except (AttributeError, Exception):  # pragma: no cover - best-effort
                pass
            close_pools()

    app = FastAPI(title=settings.app_title, lifespan=lifespan)
    app.state.settings = settings
    app.state.conversation_service = ConversationService(settings)
    app.add_middleware(SessionMiddleware, settings=settings)

    @app.middleware("http")
    async def rate_limit_api(request: Request, call_next: Any) -> Response:
        if request.url.path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"}:
            client_ip = _client_ip(request)
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


def _assert_embedding_dimensions(settings: Settings) -> None:
    """Fail fast if `EMBEDDING_DIMENSIONS` no longer matches the rag_documents column."""
    try:
        with connect_dict(settings) as conn:
            row = conn.execute(
                """
                SELECT format_type(a.atttypid, a.atttypmod) AS column_type
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                WHERE c.relname = 'rag_documents' AND a.attname = 'embedding'
                """
            ).fetchone()
    except Exception:
        logger.warning("startup.embedding_dim_check.skipped reason=db_unreachable")
        return
    if not row:
        return
    column_type = str(row["column_type"])
    column_dim = _parse_vector_dimensions(column_type)
    if column_dim and column_dim != settings.embedding_dimensions:
        raise RuntimeError(
            f"EMBEDDING_DIMENSIONS={settings.embedding_dimensions} does not match the "
            f"rag_documents.embedding column type ({column_type!r}). Run a migration to "
            "rebuild the column before changing models."
        )


def _parse_vector_dimensions(column_type: str) -> int | None:
    if "(" not in column_type or not column_type.endswith(")"):
        return None
    try:
        return int(column_type.split("(", 1)[1].rstrip(")"))
    except ValueError:
        return None


def _client_ip(request: Request) -> str:
    peer_host = request.client.host if request.client else "unknown"
    if peer_host in TRUSTED_PROXY_HOSTS:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        forwarded_host = forwarded_for.split(",", 1)[0].strip()
        if forwarded_host:
            return forwarded_host
    return peer_host


app = create_app()
