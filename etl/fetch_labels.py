"""
Surfline ratings ETL — forecast (no auth) + historical (access token required).

--- HOW TO GET YOUR ACCESS TOKEN ---
1. Go to surfline.com and log in
2. Open DevTools (F12) → Network tab → filter by Fetch/XHR
3. Change the date range on any surf report page
4. Right-click one of the kbyg requests → Copy → Copy as cURL
5. Find &accesstoken=... in the URL — copy that value

--- SET IT AS AN ENVIRONMENT VARIABLE ---
    export SURFLINE_ACCESS_TOKEN="your_token_here"

--- RUN TEST FIRST (one 17-day chunk, Blacks Beach, Jan 2023) ---
    python -m etl.fetch_labels --test-historical

    If you see rows with POOR/FAIR/GOOD/EPIC → success, run the full fetch.
    If you see 0 rows → the rating endpoint does not support start= historically.

--- RUN FULL HISTORICAL FETCH (2022-2024, all 3 breaks) ---
    python -m etl.fetch_labels --historical --start 2022-01-01 --end 2024-12-31 \
        --out data/processed/surfline_labels.csv

--- FORECAST MODE (no token needed) ---
    python -m etl.fetch_labels

Output columns:
  timestamp_utc  — timezone-aware UTC
  break_id       — la_jolla_shores / blacks / pb_point
  rating_key     — POOR / FAIR / GOOD / EPIC
  rating_value   — 1 / 2 / 3 / 4
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

from etl.config import SURFLINE_CACHE_DIR, SURFLINE_SPOT_IDS

log = logging.getLogger(__name__)

RATING_URL = "https://services.surfline.com/kbyg/spots/forecasts/rating"

_BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Origin": "https://www.surfline.com",
    "Referer": "https://www.surfline.com/",
}

_CHUNK_DAYS = 17      # days per API call
_REQUEST_DELAY = 2.0  # seconds between requests — don't hammer the API


# ---------------------------------------------------------------------------
# Token helper
# ---------------------------------------------------------------------------

def _get_token() -> str | None:
    token = os.environ.get("SURFLINE_ACCESS_TOKEN", "").strip()
    return token if token else None


# ---------------------------------------------------------------------------
# Single chunk fetch
# ---------------------------------------------------------------------------

def _fetch_chunk(
    spot_id: str,
    start_date: str | None = None,
    days: int = _CHUNK_DAYS,
    cache_path: Path | None = None,
) -> list[dict]:
    """
    Fetch one chunk of ratings from Surfline.

    start_date : "YYYY-MM-DD" string anchor for historical requests.
                 None = current forecast (no token needed).
    Returns raw list of rating entry dicts.
    """
    params: dict = {
        "spotId": spot_id,
        "days": days,
        "cacheEnabled": "false",
    }

    token = _get_token()
    if token:
        params["accesstoken"] = token

    if start_date is not None:
        params["start"] = start_date

    resp = requests.get(RATING_URL, params=params, headers=_BASE_HEADERS, timeout=15)

    if resp.status_code == 401:
        raise PermissionError(
            "Surfline returned 401 Unauthorized.\n"
            "Your access token is missing or wrong.\n"
            "Set SURFLINE_ACCESS_TOKEN (see module docstring)."
        )
    if resp.status_code == 403:
        raise PermissionError(
            "Surfline returned 403 Forbidden.\n"
            "Your token has likely expired — grab a fresh one from the Network tab."
        )
    resp.raise_for_status()

    data = resp.json()

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, indent=2))

    try:
        return data["data"]["rating"]
    except (KeyError, TypeError):
        log.warning("Unexpected response shape. Top-level keys: %s", list(data.keys()))
        return []


# ---------------------------------------------------------------------------
# Forecast fetch (no token needed)
# ---------------------------------------------------------------------------

def fetch_ratings_for_break(
    break_id: str,
    spot_id: str,
    days: int = 5,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Fetch upcoming forecast ratings for one break. No token required."""
    cache_path = (Path(cache_dir) / f"{break_id}_forecast.json") if cache_dir else None
    entries = _fetch_chunk(spot_id, start_date=None, days=days, cache_path=cache_path)
    return _entries_to_df(entries, break_id)


def fetch_all_ratings(days: int = 5, cache_dir: Path | None = None) -> pd.DataFrame:
    """Fetch forecast ratings for all breaks. No token required."""
    frames = []
    for break_id, spot_id in SURFLINE_SPOT_IDS.items():
        df = fetch_ratings_for_break(break_id, spot_id, days, cache_dir)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Historical fetch (access token required)
# ---------------------------------------------------------------------------

def fetch_ratings_historical(
    start: datetime,
    end: datetime,
    break_ids: list[str] | None = None,
    cache_dir: Path | None = None,
    chunk_days: int = _CHUNK_DAYS,
) -> pd.DataFrame:
    """
    Fetch historical hourly ratings for a date range across breaks.

    Requires SURFLINE_ACCESS_TOKEN env var.
    Loops in chunk_days windows, caches each chunk — safe to re-run,
    already-fetched chunks are skipped.

    Returns DataFrame with: timestamp_utc, break_id, rating_key, rating_value
    """
    if _get_token() is None:
        raise EnvironmentError(
            "SURFLINE_ACCESS_TOKEN is not set.\n"
            "See the module docstring for how to get it."
        )

    if break_ids is None:
        break_ids = list(SURFLINE_SPOT_IDS.keys())

    if cache_dir is None:
        cache_dir = SURFLINE_CACHE_DIR / "historical"
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    all_frames: list[pd.DataFrame] = []

    for break_id in break_ids:
        spot_id = SURFLINE_SPOT_IDS.get(break_id)
        if spot_id is None:
            log.warning("Unknown break_id '%s' — skipping", break_id)
            continue

        print(f"\n[{break_id}] fetching {start.date()} → {end.date()}")
        chunk_start = start

        while chunk_start < end:
            chunk_end = min(chunk_start + timedelta(days=chunk_days), end)
            start_str = chunk_start.strftime("%Y-%m-%d")
            cache_fname = cache_dir / f"{break_id}_{start_str}.json"

            if cache_fname.exists():
                print(f"  {start_str} — cached, skipping")
                raw = json.loads(cache_fname.read_text())
                entries = raw.get("data", {}).get("rating", [])
            else:
                print(f"  {start_str} → {chunk_end.date()} — fetching...", end=" ", flush=True)
                try:
                    _fetch_chunk(
                        spot_id,
                        start_date=start_str,
                        days=chunk_days,
                        cache_path=cache_fname,
                    )
                    raw = json.loads(cache_fname.read_text())
                    entries = raw.get("data", {}).get("rating", [])
                except PermissionError:
                    raise
                except requests.RequestException as exc:
                    print(f"FAILED ({exc}) — skipping")
                    chunk_start = chunk_end
                    continue
                time.sleep(_REQUEST_DELAY)

            df = _entries_to_df(entries, break_id)
            df = df[
                (df["timestamp_utc"] >= chunk_start) &
                (df["timestamp_utc"] < chunk_end)
            ]
            print(f"{len(df)} rows")
            if not df.empty:
                all_frames.append(df)

            chunk_start = chunk_end

    if not all_frames:
        return pd.DataFrame(columns=["timestamp_utc", "break_id", "rating_key", "rating_value"])

    return (
        pd.concat(all_frames, ignore_index=True)
        .sort_values("timestamp_utc")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Shared parser
# ---------------------------------------------------------------------------

def _entries_to_df(entries: list[dict], break_id: str) -> pd.DataFrame:
    if not entries:
        return pd.DataFrame(columns=["timestamp_utc", "break_id", "rating_key", "rating_value"])
    rows = []
    for entry in entries:
        try:
            rows.append({
                "timestamp_utc": pd.Timestamp(entry["timestamp"], unit="s", tz="UTC"),
                "break_id": break_id,
                "rating_key": entry["rating"]["key"],
                "rating_value": entry["rating"]["value"],
            })
        except (KeyError, TypeError) as e:
            log.debug("Skipping malformed entry: %s — %s", entry, e)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    p = argparse.ArgumentParser(description="Fetch Surfline surf ratings")
    p.add_argument("--historical", action="store_true",
                   help="Fetch historical ratings (requires SURFLINE_ACCESS_TOKEN)")
    p.add_argument("--test-historical", action="store_true",
                   help="Fetch ONE chunk (Jan 1-17 2023, Blacks) to verify token + start= work")
    p.add_argument("--start", default="2022-01-01", help="Start date YYYY-MM-DD")
    p.add_argument("--end",   default="2024-12-31", help="End date YYYY-MM-DD")
    p.add_argument("--break-ids", nargs="+", default=None,
                   help="Specific breaks e.g. --break-ids blacks pb_point")
    p.add_argument("--out", type=Path, default=None,
                   help="Save combined CSV here e.g. data/processed/surfline_labels.csv")
    args = p.parse_args()

    if args.test_historical:
        print("=== TEST: Jan 1-17 2023, Blacks Beach ===")
        print(f"Token: {'SET' if _get_token() else 'NOT SET — run: export SURFLINE_ACCESS_TOKEN=your_token'}")
        df = fetch_ratings_historical(
            start=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end=datetime(2023, 1, 17, tzinfo=timezone.utc),
            break_ids=["blacks"],
            cache_dir=SURFLINE_CACHE_DIR / "test",
        )
        if df.empty:
            print("\nRESULT: 0 rows")
            print("The rating endpoint does not support start= for historical data.")
            print("Next step: find a 'rating' request (not tides) in the Network tab")
            print("and check whether its URL also has a start= parameter.")
        else:
            print(f"\nRESULT: {len(df)} rows — SUCCESS")
            print(df.to_string())
            print("\nRating breakdown:")
            print(df["rating_key"].value_counts().to_string())
            print("\nRun the full fetch:")
            print("  python -m etl.fetch_labels --historical --out data/processed/surfline_labels.csv")
        return

    if args.historical:
        start = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end   = datetime.strptime(args.end,   "%Y-%m-%d").replace(tzinfo=timezone.utc)
        print(f"=== Historical fetch: {start.date()} → {end.date()} ===")
        df = fetch_ratings_historical(
            start=start,
            end=end,
            break_ids=args.break_ids,
            cache_dir=SURFLINE_CACHE_DIR / "historical",
        )
    else:
        print("=== Forecast fetch (next 5 days, no token needed) ===")
        df = fetch_all_ratings(days=5, cache_dir=SURFLINE_CACHE_DIR)

    print(f"\n{df.head(12).to_string()}")
    print(f"\nTotal rows: {len(df)}")
    if not df.empty:
        print("\nRating breakdown:")
        print(df["rating_key"].value_counts().to_string())

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.out, index=False)
        print(f"\nSaved → {args.out}")


if __name__ == "__main__":
    main()
