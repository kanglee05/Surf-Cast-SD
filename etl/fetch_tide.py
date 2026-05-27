"""
Week 2 — Tide ETL

Fetches hourly tide heights from NOAA CO-OPS for station 9410170 (La Jolla).
Handles requests longer than 31 days by chunking (API limit for water_level).
Caches raw JSON under data/raw/noaa_tides/.

Output contract (fetch_tide_heights)
-------------------------------------
Returns a DataFrame with:
- timestamp_utc  — timezone-aware UTC
- tide_height_m  — water level in metres above MLLW

Run from repo root:
    python -m etl.fetch_tide
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

from etl.config import NOAA_TIDES_CACHE_DIR, TIDE_STATION

log = logging.getLogger(__name__)

_BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
_CHUNK_DAYS = 30  # stay safely under the 31-day API limit


def _fetch_chunk(
    station: str,
    begin: datetime,
    end: datetime,
    cache_dir: Path | None,
) -> list[dict]:
    """Fetch one ≤31-day chunk of hourly water_level data. Returns raw records."""
    params = {
        "station": station,
        "product": "water_level",
        "datum": "MLLW",
        "time_zone": "GMT",
        "units": "metric",
        "interval": "h",
        "format": "json",
        "begin_date": begin.strftime("%Y%m%d"),
        "end_date": end.strftime("%Y%m%d"),
    }

    resp = requests.get(_BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    payload = resp.json()

    if "error" in payload:
        log.warning("NOAA CO-OPS error for %s–%s: %s", begin.date(), end.date(), payload["error"])
        return []

    records = payload.get("data", [])

    if cache_dir is not None:
        fname = f"{station}_{begin.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.json"
        (cache_dir / fname).write_text(json.dumps(records, indent=2))

    return records


def fetch_tide_heights(
    station: str = TIDE_STATION,
    days: int = 30,
    use_cache: bool = False,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """
    Return hourly tide heights for the last ``days`` days.

    Chunks requests into ≤30-day windows to stay within the NOAA API limit.
    If ``use_cache`` is True and a cached file exists for a chunk, skips re-fetching.
    """
    if cache_dir is None:
        cache_dir = NOAA_TIDES_CACHE_DIR
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=days)

    all_records: list[dict] = []
    chunk_start = start

    while chunk_start < end:
        chunk_end = min(chunk_start + timedelta(days=_CHUNK_DAYS), end)

        cache_fname = cache_dir / f"{station}_{chunk_start.strftime('%Y%m%d')}_{chunk_end.strftime('%Y%m%d')}.json"
        if use_cache and cache_fname.exists():
            all_records.extend(json.loads(cache_fname.read_text()))
            log.info("Loaded tide cache: %s", cache_fname.name)
        else:
            try:
                records = _fetch_chunk(station, chunk_start, chunk_end, cache_dir)
                all_records.extend(records)
            except requests.RequestException as exc:
                log.warning("Tide fetch failed for %s–%s: %s — skipping chunk", chunk_start.date(), chunk_end.date(), exc)

        chunk_start = chunk_end + timedelta(hours=1)

    if not all_records:
        log.warning("No tide data retrieved for station %s", station)
        return pd.DataFrame(columns=["timestamp_utc", "tide_height_m"])

    df = pd.DataFrame(all_records)
    df["timestamp_utc"] = pd.to_datetime(df["t"], utc=True)
    df["tide_height_m"] = pd.to_numeric(df["v"], errors="coerce")

    # NOAA water_level ignores interval=h — resample to hourly mean
    df = (
        df.set_index("timestamp_utc")[["tide_height_m"]]
        .resample("h")
        .mean()
        .reset_index()
    )

    return df.sort_values("timestamp_utc").reset_index(drop=True)


def main() -> None:
    df = fetch_tide_heights(days=30)
    print(df.head(12))
    print("rows:", len(df))


if __name__ == "__main__":
    main()
