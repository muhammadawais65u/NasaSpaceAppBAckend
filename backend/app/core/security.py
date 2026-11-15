from dataclasses import dataclass

import httpx
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.errors import ApiError

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    id: str      # taken ONLY from the verified token
    token: str   # passed on so reads run as this user (RLS)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> AuthUser:
    if creds is None:
        raise ApiError(401, "missing_token", "Sign in required.")
    try:
        r = httpx.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={"Authorization": f"Bearer {creds.credentials}",
                     "apikey": settings.supabase_anon_key},
            timeout=5.0)
    except httpx.HTTPError:
        raise ApiError(503, "auth_unavailable", "Sign-in service unreachable.")
    if r.status_code != 200:
        raise ApiError(401, "invalid_token", "Token is invalid or expired.")
    return AuthUser(id=r.json()["id"], token=creds.credentials)
