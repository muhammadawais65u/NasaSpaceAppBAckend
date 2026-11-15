"""NASA Open Science Data Repository (OSDR): real space-biology studies by keyword."""
import logging
import time
from datetime import datetime, timezone

import httpx

log = logging.getLogger("osdr")

OSDR_SEARCH = "https://osdr.nasa.gov/osdr/data/search"
STUDY_URL = "https://osdr.nasa.gov/bio/repo/data/studies/"
CACHE_TTL_SECONDS = 6 * 60 * 60
ATTRIBUTION = "NASA Open Science Data Repository (OSDR), osdr.nasa.gov"

_cache: dict[tuple[str, int], tuple[float, dict]] = {}


def _study(src: dict) -> dict | None:
    accession = src.get("Accession") or src.get("Study Identifier")
    title = src.get("Study Title")
    if not accession or not title:
        return None
    released = src.get("Study Public Release Date")
    return {
        "accession": accession,
        "title": title,
        "description": src.get("Study Description") or None,
        "organism": src.get("organism") or None,
        "project_type": src.get("Project Type") or None,
        "flight_program": src.get("Flight Program") or None,
        "mission": (src.get("Mission") or {}).get("Name") or None,
        "release_date": (datetime.fromtimestamp(released, timezone.utc).date().isoformat()
                         if isinstance(released, (int, float)) else None),
        "link": STUDY_URL + accession,
    }


def fetch_studies(term: str, limit: int) -> dict:
    with httpx.Client(timeout=15.0) as client:
        r = client.get(OSDR_SEARCH, params={"term": term, "from": 0, "size": limit,
                                            "type": "cgene"})
    r.raise_for_status()
    hits = r.json()["hits"]
    studies = [s for s in (_study(h.get("_source") or {}) for h in hits["hits"]) if s]
    return {"total_matches": hits.get("total"), "studies": studies}


def search_studies(term: str, limit: int = 5) -> dict:
    key = (term.strip().lower(), limit)
    cached = _cache.get(key)
    status = "live"
    if not cached or time.time() - cached[0] >= CACHE_TTL_SECONDS:
        try:
            cached = _cache[key] = (time.time(), fetch_studies(key[0], limit))
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            log.warning("OSDR search failed: %s", type(exc).__name__)
            status = "cached" if cached else "unavailable"
    body = cached[1] if cached else {"total_matches": None, "studies": []}
    return {
        "data_status": status,
        "source": "NASA OSDR",
        "attribution": ATTRIBUTION,
        "term": key[0],
        "retrieved_at": (datetime.fromtimestamp(cached[0], timezone.utc).isoformat()
                         if cached else None),
        **body,
    }
