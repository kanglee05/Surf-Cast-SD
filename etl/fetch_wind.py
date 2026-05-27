"""
Week 1 — Wind ETL (your team implements this file)

Goal
----
For each surf break in ``etl.config.BREAKS``, call **api.weather.gov** and build a **long-format**
DataFrame of **hourly** wind suitable for merging with buoy data.

Suggested output columns (names matter for ``merge_hourly``)
------------------------------------------------------------
- ``timestamp_utc``
- ``break_id`` — same keys as in ``BREAKS`` (e.g. ``la_jolla_shores``)
- ``wind_speed_mph`` — numeric (or pick one unit and **document it** in README)
- ``wind_direction_degrees`` — numeric degrees, or document if you keep compass strings

API flow (typical)
------------------
1. ``GET https://api.weather.gov/points/{lat},{lon}`` with headers including **User-Agent**
   (set ``NWS_USER_AGENT`` in ``etl/config.py``).
2. Read ``properties.forecastHourly`` from the JSON; ``GET`` that URL for hourly periods.
3. Parse ``windSpeed`` (often a string like ``"5 mph"``) and ``windDirection`` (often ``"NW"``).

Gotchas (read before coding)
-----------------------------
- Some **beach-only** coordinates return **404** / “Marine Forecast Not Supported” for hourly.
  You may need slightly **inland** proxy coordinates — validate with your mentor what “close enough” means.
- ``forecast/hourly`` is a **forecast**, not historical observations. If the club’s Week 1 spec
  requires *past* wind only, ask the mentor which archive to use instead (METAR, etc.).

Checklist
---------
- [ ] Respect NWS ``User-Agent`` policy (descriptive string, contact or repo URL).
- [ ] Optional: save raw JSON under ``data/raw/nws/`` for debugging (gitignored).
- [ ] ``python -m etl.fetch_wind`` prints a sensible ``head()`` from repo root.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import pandas as pd
import requests

from etl.config import BREAKS, NWS_CACHE_DIR, NWS_USER_AGENT

log = logging.getLogger(__name__)

COMPASS_TO_DEGREES = {
    "N": 0, "NNE": 22, "NE": 45, "ENE": 67,
    "E": 90, "ESE": 112, "SE": 135, "SSE": 157,
    "S": 180, "SSW": 202, "SW": 225, "WSW": 247,
    "W": 270, "WNW": 292, "NW": 315, "NNW": 337,
}


def parse_wind_speed(speed_str: str) -> float:
    """Parse NWS wind speed string to mph.

    Handles: "Calm", "5 mph", "5 to 10 mph" (returns max of range).
    """
    if not speed_str or speed_str.strip().lower() == "calm":
        return 0.0
    numbers = re.findall(r"\d+(?:\.\d+)?", speed_str)
    if not numbers:
        return 0.0
    return float(max(numbers, key=float))


def fetch_wind_all_breaks(
    breaks: dict[str, tuple[float, float]] | None = None,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """
    Return concatenated long-format hourly wind for every break in ``breaks``
    (default: ``BREAKS``). ``cache_dir`` may be ``NWS_CACHE_DIR`` to stash JSON snapshots.
    """
    if breaks is None:
        breaks = BREAKS

    headers = {"User-Agent": NWS_USER_AGENT, "Accept": "application/geo+json"}
    all_frames = []

    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

    for break_id, (lat, lon) in breaks.items():
        try:
            points_resp = requests.get(
                f"https://api.weather.gov/points/{lat},{lon}",
                headers=headers,
                timeout=15,
            )
            if points_resp.status_code == 404:
                log.warning("NWS /points 404 for %s (%s,%s) — skipping", break_id, lat, lon)
                continue
            points_resp.raise_for_status()

            forecast_hourly_url = points_resp.json()["properties"].get("forecastHourly")
            if not forecast_hourly_url:
                log.warning("forecastHourly is null for %s — skipping", break_id)
                continue

            forecast_resp = requests.get(
                forecast_hourly_url,
                headers=headers,
                timeout=15,
            )
            if forecast_resp.status_code == 404:
                log.warning("forecastHourly 404 for %s — skipping", break_id)
                continue
            forecast_resp.raise_for_status()

            periods = forecast_resp.json()["properties"]["periods"]
        except requests.RequestException as exc:
            log.warning("Request failed for %s: %s — skipping", break_id, exc)
            continue

        if cache_dir is not None:
            (cache_dir / f"{break_id}_hourly.json").write_text(json.dumps(periods, indent=2))

        rows = []
        for period in periods:
            speed_mph = parse_wind_speed(period.get("windSpeed", ""))
            direction_deg = COMPASS_TO_DEGREES.get(period.get("windDirection", "N").upper())
            rows.append({
                "timestamp_utc": pd.Timestamp(period["startTime"]).tz_convert("UTC"),
                "break_id": break_id,
                "wind_speed_mph": speed_mph,
                "wind_direction_degrees": direction_deg,
            })

        all_frames.append(pd.DataFrame(rows))

    if not all_frames:
        log.warning("No wind data fetched — all breaks skipped")
        return pd.DataFrame(columns=["timestamp_utc", "break_id", "wind_speed_mph", "wind_direction_degrees"])
    return pd.concat(all_frames, ignore_index=True)


def main() -> None:
    try:
        NWS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df = fetch_wind_all_breaks(cache_dir=NWS_CACHE_DIR)
        print(df.head(12))
        print("rows:", len(df))
    except NotImplementedError:
        print("Implement this module — start at the docstring at the top of etl/fetch_wind.py")


if __name__ == "__main__":
    main()
