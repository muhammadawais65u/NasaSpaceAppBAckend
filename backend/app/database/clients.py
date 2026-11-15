from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def service_client() -> Client:
    """PRIVILEGED: bypasses RLS. Server-side only."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def user_client(access_token: str) -> Client:
    """Acts as the signed-in player: RLS applies to every query."""
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(access_token)
    return client
