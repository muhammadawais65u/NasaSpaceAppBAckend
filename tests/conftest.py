import os

# Tests always run against local SQLite and never call Supabase or NASA.
for key in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY", "DEMO_FORCE_ALERT"):
    os.environ[key] = ""
os.environ["NASA_API_KEY"] = "test-key"

from datetime import datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services import nasa_service as nasa  # noqa: E402


def donki_time(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%MZ")


@pytest.fixture
def donki(monkeypatch):
    """Fake DONKI replies per event type; an Exception value simulates an outage."""
    replies = {"FLR": [], "CME": [], "GST": []}

    def fake_fetch(event_type, start, end):
        reply = replies[event_type]
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(nasa, "fetch_donki", fake_fetch)
    return replies


@pytest.fixture
def client(tmp_path, monkeypatch, donki):
    monkeypatch.setattr(settings, "local_db_path", str(tmp_path / "test.db"))
    nasa._synced.clear()
    nasa._failed_at.clear()
    return TestClient(app)


def auth(player: str = "alice") -> dict:
    return {"Authorization": f"Bearer {player}"}
