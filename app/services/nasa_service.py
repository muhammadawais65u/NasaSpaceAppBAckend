import logging
import time
from datetime import date, datetime, timedelta, timezone

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.database import repository as repo

log = logging.getLogger("nasa")
logging.getLogger("httpx").setLevel(logging.WARNING)  # URLs contain api_key

DONKI_BASE = "https://api.nasa.gov/DONKI"
EVENT_TYPES = ("FLR", "CME", "GST")
CACHE_TTL_SECONDS = 30 * 60
FAILURE_BACKOFF_SECONDS = 2 * 60
MAX_WINDOW_DAYS = 60  # DONKI rejects longer date ranges
MAX_EVENTS = 200
SCENARIO_LOOKBACK_DAYS = 7  # GAME DESIGN
ATTRIBUTION = ("NASA DONKI (Space Weather Database Of Notifications, Knowledge, "
               "Information), api.nasa.gov")

_synced: dict[str, tuple[float, date]] = {}
_failed_at: dict[str, float] = {}


class NormalizedEvent(BaseModel):
    external_event_id: str
    event_type: str
    event_date: datetime
    title: str
    details: dict
    link: str | None = None


def fetch_donki(event_type: str, start: date, end: date) -> list[dict]:
    params = {"startDate": start.isoformat(), "endDate": end.isoformat(),
              "api_key": settings.nasa_api_key}
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{DONKI_BASE}/{event_type}", params=params)
    r.raise_for_status()
    if not r.content:
        return []
    data = r.json()
    if not isinstance(data, list):
        raise ValueError("Unexpected DONKI response shape")
    return data


def normalize(event_type: str, rec: dict) -> NormalizedEvent | None:
    try:
        if event_type == "FLR":
            return NormalizedEvent(
                external_event_id=rec["flrID"], event_type="FLR",
                event_date=rec["beginTime"],
                title=f"Solar flare, class {rec.get('classType') or 'unknown'}",
                details={"class_type": rec.get("classType"),
                         "peak_time": rec.get("peakTime"),
                         "source_location": rec.get("sourceLocation")},
                link=rec.get("link"))
        if event_type == "CME":
            best = next((a for a in rec.get("cmeAnalyses") or []
                         if a.get("isMostAccurate")), {})
            return NormalizedEvent(
                external_event_id=rec["activityID"], event_type="CME",
                event_date=rec["startTime"], title="Coronal mass ejection",
                details={"source_location": rec.get("sourceLocation"),
                         "note": rec.get("note"),
                         "speed_km_s": best.get("speed")},
                link=rec.get("link"))
        if event_type == "GST":
            kps = [k["kpIndex"] for k in rec.get("allKpIndex") or []
                   if isinstance(k.get("kpIndex"), (int, float))]
            return NormalizedEvent(
                external_event_id=rec["gstID"], event_type="GST",
                event_date=rec["startTime"], title="Geomagnetic storm",
                details={"max_kp_index": max(kps) if kps else None},
                link=rec.get("link"))
    except (KeyError, TypeError, AttributeError, ValidationError) as exc:
        log.warning("Skipping malformed %s record: %s", event_type, type(exc).__name__)
    return None


def cache_events(pairs: list[tuple[NormalizedEvent, dict]], origin="live_api"):
    now = datetime.now(timezone.utc).isoformat()
    rows = [{
        "source": "NASA DONKI",
        "external_event_id": e.external_event_id,
        "event_type": e.event_type,
        "event_date": e.event_date.astimezone(timezone.utc).isoformat(),
        "event_data": raw,
        "summary": {"title": e.title, "details": e.details, "link": e.link},
        "data_origin": origin,
        "retrieved_at": now,
    } for e, raw in pairs]
    if rows:
        repo.upsert_events(rows)


def _sync(event_type: str, start: date, end: date) -> bool:
    """True when the cache holds a fresh NASA answer for this type and window."""
    now = time.time()
    synced = _synced.get(event_type)
    if synced and now - synced[0] < CACHE_TTL_SECONDS and synced[1] <= start:
        return True
    if now - _failed_at.get(event_type, 0) < FAILURE_BACKOFF_SECONDS:
        return False
    try:
        raw = fetch_donki(event_type, start, end)
    except (httpx.HTTPError, ValueError) as exc:
        _failed_at[event_type] = now
        log.warning("DONKI %s failed: %s", event_type, type(exc).__name__)
        return False
    pairs = [(normalize(event_type, r), r) for r in raw if isinstance(r, dict)]
    try:
        cache_events([(e, r) for e, r in pairs if e])
    except repo.DatabaseError as exc:
        log.warning("Caching %s events failed: %s", event_type, type(exc).__name__)
        return False
    _synced[event_type] = (now, start)
    return True


def get_space_weather(types=EVENT_TYPES, days: int = 30) -> dict:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=min(days, MAX_WINDOW_DAYS))
    fresh = {t: _sync(t, start, end) for t in types}
    rows = repo.read_events(types, start.isoformat(), MAX_EVENTS)

    have = {r["event_type"] for r in rows}
    type_status = {t: "live" if fresh[t] else "cached" if t in have else "unavailable"
                   for t in types}
    if not any(fresh.values()) and not rows:
        status = "unavailable"
    elif rows and all(r["data_origin"] == "archive" for r in rows):
        status = "archived"
    elif all(fresh[r["event_type"]] for r in rows):
        status = "live"
    else:
        status = "cached"
    return {
        "data_status": status,
        "type_status": type_status,
        "source": "NASA DONKI",
        "attribution": ATTRIBUTION,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "retrieved_at": max((r["retrieved_at"] for r in rows), default=None),
        "events": rows,
    }


def derive_alert(rows: list[dict]) -> dict:
    """GAME DESIGN rule. Converts observations into a simulated alert."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=SCENARIO_LOOKBACK_DAYS)
    level, basis = "calm", None
    for r in rows:  # newest first
        if datetime.fromisoformat(r["event_date"]) < cutoff:
            continue
        cls = (r["summary"]["details"].get("class_type") or "")[:1]
        if r["event_type"] == "GST":
            level, basis = "storm", r
            break
        if (r["event_type"] == "CME" or cls in ("M", "X")) and level == "calm":
            level, basis = "watch", r
    why = ("Game alert derived from recent NASA events. Not a NASA measurement."
           if basis else "No qualifying NASA events (or no data): calm game scenario.")
    return {"alert_level": level, "is_simulation": True,
            "basis_event_id": basis["id"] if basis else None,
            "explanation": why}
