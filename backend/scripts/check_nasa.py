"""Run: python scripts/check_nasa.py
Checks your NASA key and prints the REAL field names DONKI returns,
so you can confirm normalize() in nasa_service.py matches."""
import os
from datetime import date, timedelta

import httpx
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("NASA_API_KEY")
end = date.today()
start = end - timedelta(days=30)

for t in ("FLR", "CME", "GST", "SEP"):
    r = httpx.get(f"https://api.nasa.gov/DONKI/{t}", params={
        "startDate": start.isoformat(), "endDate": end.isoformat(),
        "api_key": key}, timeout=15)
    data = r.json() if r.content else []
    print(f"{t}: HTTP {r.status_code}, {len(data) if isinstance(data, list) else '?'} events")
    if isinstance(data, list) and data:
        print("   fields:", list(data[0].keys()))
