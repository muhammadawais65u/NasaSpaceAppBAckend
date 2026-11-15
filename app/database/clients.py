from functools import lru_cache

import httpx
from postgrest import SyncPostgrestClient
from supabase import Client, create_client

from app.core.config import settings

_http = httpx.Client(timeout=15.0, follow_redirects=True)


@lru_cache
def service_client() -> Client:
    """PRIVILEGED: bypasses RLS. Server-side only."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def user_client(access_token: str) -> SyncPostgrestClient:
    """Acts as the signed-in player: RLS applies to every query.
    Shares one HTTP connection pool instead of opening connections per request."""
    return SyncPostgrestClient(
        f"{settings.supabase_url}/rest/v1",
        headers={"apikey": settings.supabase_anon_key,
                 "Authorization": f"Bearer {access_token}"},
        http_client=_http)
