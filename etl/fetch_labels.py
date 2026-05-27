"""
Week 2 — Surfline ratings ETL

Fetches hourly surf ratings from Surfline's unofficial rating endpoint.
No login required for forecast ratings (up to 5 days ahead).

Output columns:
- timestamp_utc  — timezone-aware UTC
- break_id       — matches BREAKS keys in config.py
- rating_key     — Surfline category string (POOR, FAIR, GOOD, etc.)
- rating_value   — numeric score (0-5 scale)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests

from etl.config import SURFLINE_CACHE_DIR, SURFLINE_SPOT_IDS

RATING_URL = "https://services.surfline.com/kbyg/spots/forecasts/rating"

HEADERS = {
    "User-Agent": "SurfCastSD/0.1 (college project; https://github.com/Igosain08/surfcastSD)"
}


def fetch_ratings_for_break(
    break_id: str,
    spot_id: str,
    days: int = 5,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Fetch hourly ratings for one break. Returns clean DataFrame."""
    resp = requests.get(
        RATING_URL,
        params={"spotId": spot_id, "days": days},
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{break_id}_ratings.json").write_text(
            json.dumps(data, indent=2)
        )

    rows = []
    for entry in data["data"]["rating"]:
        rows.append({
            "timestamp_utc": pd.Timestamp(entry["timestamp"], unit="s", tz="UTC"),
            "break_id": break_id,
            "rating_key": entry["rating"]["key"],
            "rating_value": entry["rating"]["value"],
        })

    return pd.DataFrame(rows)


def fetch_all_ratings(
    days: int = 5,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Fetch ratings for all breaks and return combined DataFrame."""
    all_frames = []

    for break_id, spot_id in SURFLINE_SPOT_IDS.items():
        df = fetch_ratings_for_break(break_id, spot_id, days, cache_dir)
        all_frames.append(df)

    return pd.concat(all_frames, ignore_index=True)


def main() -> None:
    df = fetch_all_ratings(days=5, cache_dir=SURFLINE_CACHE_DIR)
    print(df.head(12))
    print("rows:", len(df))


if __name__ == "__main__":
    main()