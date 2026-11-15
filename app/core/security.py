from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

import httpx
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.errors import ApiError

bearer = HTTPBearer(auto_error=False)
_auth_http = httpx.Client(timeout=8.0)


@dataclass(frozen=True)
class AuthUser:
    id: str
    token: str


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> AuthUser:
    if creds is None:
        raise ApiError(401, "missing_token", "Sign in required.")
    if not settings.use_supabase:
        # Local development only: no real sign-in, each distinct token is its own player.
        return AuthUser(id=str(uuid5(NAMESPACE_URL, f"local-dev:{creds.credentials}")),
                        token=creds.credentials)
    headers = {"Authorization": f"Bearer {creds.credentials}",
               "apikey": settings.supabase_anon_key}
    for attempt in (1, 2):
        try:
            r = _auth_http.get(f"{settings.supabase_url}/auth/v1/user", headers=headers)
            break
        except httpx.HTTPError:
            if attempt == 2:
                raise ApiError(503, "auth_unavailable", "Sign-in service unreachable.")
    if r.status_code != 200:
        raise ApiError(401, "invalid_token", "Token is invalid or expired.")
    return AuthUser(id=r.json()["id"], token=creds.credentials)
