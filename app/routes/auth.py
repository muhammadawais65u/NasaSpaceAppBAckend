import logging
import secrets
import time
from uuid import uuid4

import httpx
from fastapi import APIRouter

from app.core.config import settings
from app.core.errors import ApiError

log = logging.getLogger("auth")
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

GUESTS_PER_MINUTE = 30
_recent: list[float] = []


@router.post("/guest", status_code=201)
def guest_session():
    """Creates a throwaway player so children can play with only a first name.
    No personal data is stored: the account has a random address and password."""
    if not settings.use_supabase:
        raise ApiError(404, "guest_sign_in_unavailable",
                       "Guest sign-in needs Supabase. In local mode send any Bearer token.")
    now = time.time()
    _recent[:] = [t for t in _recent if now - t < 60]
    if len(_recent) >= GUESTS_PER_MINUTE:
        raise ApiError(429, "too_many_requests", "Too many new players right now. Try again in a minute.")
    _recent.append(now)

    from app.database.clients import service_client

    email = f"guest-{uuid4().hex}@guest.junior-astronaut.test"
    password = secrets.token_urlsafe(32)
    try:
        service_client().auth.admin.create_user(
            {"email": email, "password": password, "email_confirm": True,
             "user_metadata": {"guest": True}})
        r = httpx.post(f"{settings.supabase_url}/auth/v1/token?grant_type=password",
                       headers={"apikey": settings.supabase_anon_key},
                       json={"email": email, "password": password}, timeout=15.0)
        r.raise_for_status()
        session = r.json()
    except Exception as exc:
        log.warning("Guest sign-in failed: %s", type(exc).__name__)
        raise ApiError(503, "auth_unavailable", "Sign-in service unreachable.")
    return {k: session[k] for k in ("access_token", "refresh_token", "expires_in")}
