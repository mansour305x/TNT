"""aiohttp middleware helpers for TNT portal."""

from __future__ import annotations

import logging
import time
from functools import wraps

from aiohttp import web

from core.config import Config
from core.database import db

logger = logging.getLogger(__name__)


@web.middleware
async def error_handler_middleware(request: web.Request, handler):
    """Return JSON errors for API routes and plain responses for unexpected failures."""
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unhandled request error: %s", exc)
        if request.path.startswith("/api/"):
            return web.json_response({"error": "حدث خطأ في الخادم"}, status=500)
        return web.Response(text="حدث خطأ في الخادم", status=500)


@web.middleware
async def logging_middleware(request: web.Request, handler):
    """Log basic request timing data."""
    started_at = time.perf_counter()
    response = await handler(request)
    duration_ms = (time.perf_counter() - started_at) * 1000
    logger.info(
        "%s %s -> %s (%.2fms)",
        request.method,
        request.path,
        response.status,
        duration_ms,
    )
    return response


@web.middleware
async def session_middleware(request: web.Request, handler):
    """Load user and state sessions from cookies."""
    request["authenticated"] = False
    request["user_id"] = None
    request["state_authenticated"] = False
    request["state_id"] = None

    session_token = request.cookies.get(Config.SESSION_COOKIE_NAME)
    if session_token:
        session_data = db.fetchone(
            """
            SELECT user_id
            FROM sessions
            WHERE session_token = ?
              AND datetime(expires_at) > datetime('now')
            """,
            (session_token,),
        )
        if session_data:
            from models.user_model import User
            request["authenticated"] = True
            request["user_id"] = session_data["user_id"]
            cu = User(session_data["user_id"])
            cu.load()
            request["current_user"] = cu

    state_session_token = request.cookies.get(Config.STATE_SESSION_COOKIE_NAME)
    if state_session_token:
        state_session_data = db.fetchone(
            """
            SELECT state_id
            FROM state_sessions
            WHERE session_token = ?
              AND datetime(expires_at) > datetime('now')
            """,
            (state_session_token,),
        )
        if state_session_data:
            request["state_authenticated"] = True
            request["state_id"] = state_session_data["state_id"]

    return await handler(request)


def require_login(handler):
    """Decorator that enforces an authenticated request."""

    @wraps(handler)
    async def wrapped(request: web.Request, *args, **kwargs):
        if not request.get("authenticated"):
            return web.json_response({"error": "يجب تسجيل الدخول أولاً"}, status=401)
        return await handler(request, *args, **kwargs)

    return wrapped


def require_permission(permission: str):
    """Decorator that enforces a specific permission on the current user."""

    def decorator(handler):
        @wraps(handler)
        async def wrapped(request: web.Request, *args, **kwargs):
            if not request.get("authenticated"):
                return web.json_response({"error": "يجب تسجيل الدخول أولاً"}, status=401)

            from core.permissions import PermissionManager

            if not PermissionManager.has_permission(request["user_id"], permission):
                return web.json_response({"error": "ليس لديك صلاحية"}, status=403)

            return await handler(request, *args, **kwargs)

        return wrapped

    return decorator