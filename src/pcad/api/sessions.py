from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from pcad.config import Settings
from pcad.db import connect_dict
from pcad.models import Session


class SessionMiddleware(BaseHTTPMiddleware):
    """Attach an anonymous signed-cookie session to every request."""

    def __init__(self, app: Any, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings
        self.serializer = URLSafeTimedSerializer(settings.session_secret, salt="pcad-session")

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        session = self._load_or_create(request)
        request.state.session = session
        response = await call_next(request)
        token = self.serializer.dumps({"sid": session.session_id})
        response.set_cookie(
            self.settings.session_cookie_name,
            token,
            max_age=self.settings.session_ttl_days * 86400,
            httponly=True,
            samesite="lax",
            secure=getattr(self.settings, "session_cookie_secure", False),
        )
        if random.random() < 0.01:
            cleanup_expired_sessions(self.settings)
        return response

    def _load_or_create(self, request: Request) -> Session:
        token = request.cookies.get(self.settings.session_cookie_name)
        session_id = _load_signed_session_id(self.serializer, token, self.settings.session_ttl_days) if token else None
        if session_id:
            refreshed = _touch_and_load_session(self.settings, session_id)
            if refreshed:
                return refreshed
        return create_session(self.settings)


def create_session(settings: Settings) -> Session:
    now = datetime.now(timezone.utc)
    session = Session(session_id=str(uuid4()), created_at=now, last_seen_at=now, expires_at=now + timedelta(days=settings.session_ttl_days))
    with connect_dict(settings) as conn:
        conn.execute(
            "INSERT INTO sessions (session_id, created_at, last_seen_at, expires_at) VALUES (%s, %s, %s, %s)",
            (session.session_id, session.created_at, session.last_seen_at, session.expires_at),
        )
        conn.commit()
    return session


def cleanup_expired_sessions(settings: Settings) -> int:
    with connect_dict(settings) as conn:
        deleted = conn.execute("DELETE FROM sessions WHERE expires_at < now()").rowcount
        conn.commit()
    return int(deleted or 0)


def _load_signed_session_id(serializer: URLSafeTimedSerializer, token: str | None, ttl_days: int) -> str | None:
    if not token:
        return None
    try:
        payload = serializer.loads(token, max_age=ttl_days * 86400)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("sid"), str):
        return None
    return payload["sid"]


def _touch_and_load_session(settings: Settings, session_id: str) -> Session | None:
    """Refresh expiry and return the session in a single round-trip, or None if expired/missing."""
    with connect_dict(settings) as conn:
        row = conn.execute(
            """
            UPDATE sessions
            SET last_seen_at = now(),
                expires_at = now() + (%s || ' days')::interval
            WHERE session_id = %s AND expires_at > now()
            RETURNING session_id, created_at, last_seen_at, expires_at
            """,
            (settings.session_ttl_days, session_id),
        ).fetchone()
        conn.commit()
    return Session.model_validate(dict(row)) if row else None
