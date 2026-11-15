"""Module 1: fetch, validate, normalize, cache and honestly label NASA DONKI data."""
import logging
import time
from datetime import date, datetime, timedelta, timezone

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.database.clients import service_client  # server-side only

log = logging.getLogger("nasa")
logging.getLogger("httpx").setLevel(logging.WARNING)  # URLs contain api_key

DONKI_BASE = "https://api.nasa.gov/DONKI"
EVENT_TYPES = ("FLR", "CME", "GST")
CACHE_TTL_SECONDS = 30 * 60
SCENARIO_LOOKBACK_DAYS = 7  # GAME DESIGN parameter

_last_sync: dict[str, float] = {}


class NormalizedEvent(BaseModel):
    external_event_id: str
    event_type: str  # FLR | CME | GST
    event_date: datetime
    title: str
    details: dict
    link: str | None = None


def fetch_donki(event_type: str, start: date, end: date) -> list[dict]:
    params = {"startDate": start.isoformat(), "endDate": end.isoformat(),
              "api_key": settings.nasa_api_key}
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{DONKI_BASE}/{event_type}", params=params)
        r.raise_for_status()
        if not r.content:  # no events can come back as an empty body
            return []
        data = r.json()
    if not isinstance(data, list):
        raise ValueError("Unexpected DONKI response shape")
    return data


def normalize(event_type: str, rec: dict) -> NormalizedEvent | None:
    """Field names follow DONKI docs; confirm with scripts/check_nasa.py."""
    try:
        if event_type == "FLR":
            return NormalizedEvent(
                external_event_id=rec["flrID"], event_type="FLR",
                event_date=rec["beginTime"],
                title=f"Solar flare, class {rec.get('classType', 'unknown')}",
                details={"class_type": rec.get("classType"),
                         "peak_time": rec.get("peakTime"),
                         "source_location": rec.get("sourceLocation")},
                link=rec.get("link"))
        if event_type == "CME":
            return NormalizedEvent(
                external_event_id=rec["activityID"], event_type="CME",
                event_date=rec["startTime"], title="Coronal mass ejection",
                details={"source_location": rec.get("sourceLocation"),
                         "note": rec.get("note")},
                link=rec.get("link"))
        if event_type == "GST":
            kps = [k["kpIndex"] for k in rec.get("allKpIndex", [])
                   if isinstance(k.get("kpIndex"), (int, float))]
            return NormalizedEvent(
                external_event_id=rec["gstID"], event_type="GST",
                event_date=rec["startTime"], title="Geomagnetic storm",
                details={"max_kp_index": max(kps) if kps else None},
                link=rec.get("link"))
    except (KeyError, TypeError, ValidationError) as exc:
        log.warning("Skipping malformed %s record: %s", event_type, exc)
    return None


def cache_events(pairs: list[tuple[NormalizedEvent, dict]], origin="live_api"):
    now = datetime.now(timezone.utc).isoformat()
    rows = [{
        "source": "NASA DONKI",
        "external_event_id": e.external_event_id,
        "event_type": e.event_type,
        "event_date": e.event_date.isoformat(),
        "event_data": raw,  # verbatim NASA record
        "summary": {"title": e.title, "details": e.details, "link": e.link},
        "data_origin": origin,
        "retrieved_at": now,
    } for e, raw in pairs]
    if rows:
        service_client().table("nasa_events").upsert(
            rows, on_conflict="source,external_event_id").execute()


def read_cache(types, start: date) -> list[dict]:
    res = (service_client().table("nasa_events")
           .select("id,external_event_id,event_type,event_date,summary,"
                   "data_origin,retrieved_at")
           .in_("event_type", list(types))
           .gte("event_date", start.isoformat())
           .order("event_date", desc=True).limit(50).execute())
    return res.data


def get_space_weather(types=EVENT_TYPES, days: int = 30) -> dict:
    end = date.today()
    start = end - timedelta(days=days)
    live_ok = True
    for t in types:
        if time.time() - _last_sync.get(t, 0) < CACHE_TTL_SECONDS:
            continue  # fetched recently, use cache
        try:
            raw = fetch_donki(t, start, end)
            pairs = [(normalize(t, r), r) for r in raw]
            cache_events([(e, r) for e, r in pairs if e])
            _last_sync[t] = time.time()
        except (httpx.HTTPError, ValueError) as exc:
            live_ok = False
            log.warning("DONKI %s failed: %s", t, type(exc).__name__)
    rows = read_cache(types, start)
    if not rows:
        status = "unavailable" if not live_ok else "live"  # live + empty = calm, no events
    elif all(r["data_origin"] == "archive" for r in rows):
        status = "archived"
    elif live_ok:
        status = "live"
    else:
        status = "cached"
    return {
        "data_status": status,
        "source": "NASA DONKI",
        "attribution": "NASA DONKI (Space Weather Database Of Notifications, "
                       "Knowledge, Information), api.nasa.gov",
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "retrieved_at": max((r["retrieved_at"] for r in rows), default=None),
        "events": rows,
    }


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def derive_alert(rows: list[dict]) -> dict:
    """GAME DESIGN rule. Converts observations into a simulated alert."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=SCENARIO_LOOKBACK_DAYS)
    level, basis = "calm", None
    for r in rows:  # rows are newest first
        if _parse(r["event_date"]) < cutoff:
            continue
        cls = (r["summary"]["details"].get("class_type") or "")[:1]
        if r["event_type"] == "GST":
            level, basis = "storm", r
            break
        if r["event_type"] == "CME" or cls in ("M", "X"):
            if level == "calm":
                level, basis = "watch", r
    why = ("Game alert derived from recent NASA events. Not a NASA measurement."
           if basis else
           "No qualifying NASA events (or no data): calm game scenario.")
    return {"alert_level": level, "is_simulation": True,
            "basis_event_id": basis["id"] if basis else None,
            "explanation": why}
