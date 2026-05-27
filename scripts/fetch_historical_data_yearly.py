#!/usr/bin/env python3
"""
Fetch one year of historical data from all three sources:
  - Buoy  : NDBC yearly stdmet archive (.txt.gz) for stations 46232 + 46254
  - Tide  : NOAA CO-OPS API (same ETL, days=365)
  - Wind  : NOAA ISD hourly observations from KSAN (San Diego Airport)

Run from repo root:
    python scripts/fetch_historical_year.py --year 2024
    python scripts/fetch_historical_year.py --year 2024 --out data/processed/historical_2024.csv
"""

from __future__ import annotations

import argparse
import io
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etl.config import DATA_RAW, NDBC_STATIONS
from etl.fetch_buoy import parse_ndbc_stdmet_txt
from etl.fetch_tide import fetch_tide_heights

# NOAA ISD station ID for San Diego International Airport (KSAN)
# Used as the coastal wind proxy — ~3 miles from the ocean
KSAN_STATION_ID = "72290023188"

NDBC_HISTORICAL_URL = "https://www.ndbc.noaa.gov/data/historical/stdmet/{station}h{year}.txt.gz"
NOAA_ISD_URL = "https://www.ncei.noaa.gov/data/global-hourly/access/{year}/{station}.csv"


# ---------------------------------------------------------------------------
# Buoy
# ---------------------------------------------------------------------------

def fetch_buoy_historical(
    year: int,
    stations: tuple[str, ...] = NDBC_STATIONS,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Download full-year NDBC stdmet archive for each station, parse, concatenate."""
    if cache_dir is None:
        cache_dir = DATA_RAW / "ndbc_historical"
    cache_dir.mkdir(parents=True, exist_ok=True)

    dfs = []
    for station in stations:
        cache_path = cache_dir / f"{station}h{year}.txt.gz"
        url = NDBC_HISTORICAL_URL.format(station=station, year=year)

        if not cache_path.exists():
            print(f"  Downloading buoy {station} {year}...")
            try:
                urllib.request.urlretrieve(url, cache_path)
            except Exception as e:
                print(f"  Warning: could not download {url}: {e}")
                continue

        try:
            df = pd.read_csv(
                cache_path,
                sep=r'\s+',
                skiprows=[1],
                na_values=['MM', '99.0', '99.00', '999', '9999'],
                low_memory=False,
                compression='gzip',
            )
            df.rename(columns=lambda x: x.lstrip('#'), inplace=True)

            yr_col = 'YYYY' if 'YYYY' in df.columns else 'YY'
            date_mapping = {yr_col: 'year', 'MM': 'month', 'DD': 'day', 'hh': 'hour', 'mm': 'minute'}
            dt_df = df[list(date_mapping.keys())].rename(columns=date_mapping)
            df['timestamp_utc'] = pd.to_datetime(dt_df, errors='coerce', utc=True)

            for col in ['WVHT', 'DPD', 'MWD', 'APD']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                else:
                    df[col] = pd.NA

            df['station'] = station
            dfs.append(df[['timestamp_utc', 'station', 'WVHT', 'DPD', 'MWD', 'APD']])
            print(f"  Buoy {station} {year}: {len(df)} rows")

        except Exception as e:
            print(f"  Warning: failed to parse {cache_path.name}: {e}")

    if not dfs:
        return pd.DataFrame(columns=['timestamp_utc', 'station', 'WVHT', 'DPD', 'MWD', 'APD'])

    return pd.concat(dfs, ignore_index=True).sort_values('timestamp_utc').reset_index(drop=True)


# ---------------------------------------------------------------------------
# Tide
# ---------------------------------------------------------------------------

def fetch_tide_historical(year: int) -> pd.DataFrame:
    """Fetch one calendar year of hourly tide data via NOAA CO-OPS (chunked)."""
    from datetime import datetime, timedelta, timezone
    from etl.config import TIDE_STATION
    from etl.fetch_tide import _fetch_chunk, NOAA_TIDES_CACHE_DIR

    cache_dir = NOAA_TIDES_CACHE_DIR / "historical"
    cache_dir.mkdir(parents=True, exist_ok=True)

    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end   = datetime(year, 12, 31, 23, tzinfo=timezone.utc)

    all_records = []
    chunk_start = start
    print(f"  Fetching tide data for {year} in 30-day chunks...")
    while chunk_start <= end:
        chunk_end = min(chunk_start + timedelta(days=30), end)
        try:
            records = _fetch_chunk(TIDE_STATION, chunk_start, chunk_end, cache_dir)
            all_records.extend(records)
        except Exception as e:
            print(f"  Warning: tide chunk {chunk_start.date()}–{chunk_end.date()} failed: {e}")
        chunk_start = chunk_end + timedelta(hours=1)

    if not all_records:
        return pd.DataFrame(columns=['timestamp_utc', 'tide_height_m'])

    df = pd.DataFrame(all_records)
    df['timestamp_utc'] = pd.to_datetime(df['t'], utc=True)
    df['tide_height_m'] = pd.to_numeric(df['v'], errors='coerce')
    df = (
        df.set_index('timestamp_utc')[['tide_height_m']]
        .resample('h').mean()
        .reset_index()
    )
    print(f"  Tide {year}: {len(df)} rows")
    return df


# ---------------------------------------------------------------------------
# Wind (NOAA ISD / KSAN)
# ---------------------------------------------------------------------------

def fetch_wind_historical(
    year: int,
    station_id: str = KSAN_STATION_ID,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """
    Fetch hourly wind observations from NOAA ISD for KSAN (San Diego Airport).

    Output columns:
      timestamp_utc        — timezone-aware UTC
      wind_speed_mph       — wind speed in mph
      wind_direction_deg   — direction in degrees (0–360), NaN if variable/calm
    """
    if cache_dir is None:
        cache_dir = DATA_RAW / "isd_wind"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_path = cache_dir / f"KSAN_{year}.csv"
    url = NOAA_ISD_URL.format(year=year, station=station_id)

    if not cache_path.exists():
        print(f"  Downloading KSAN wind {year}...")
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            cache_path.write_bytes(resp.content)
        except Exception as e:
            print(f"  Warning: could not download KSAN wind {year}: {e}")
            return pd.DataFrame(columns=['timestamp_utc', 'wind_speed_mph', 'wind_direction_deg'])

    df = pd.read_csv(cache_path, low_memory=False)

    # Parse timestamp
    df['timestamp_utc'] = pd.to_datetime(df['DATE'], utc=True, errors='coerce')

    # WND field format: "direction,quality,type,speed_m_s_tenths,speed_quality"
    # e.g. "070,1,N,0103,1" → direction=70°, speed=10.3 m/s
    wnd = df['WND'].str.split(',', expand=True)
    wind_dir   = pd.to_numeric(wnd[0], errors='coerce').replace(999, np.nan)
    wind_speed_ms = pd.to_numeric(wnd[3], errors='coerce').replace(9999, np.nan) / 10

    df['wind_direction_deg'] = wind_dir
    df['wind_speed_mph']     = wind_speed_ms * 2.23694  # m/s → mph

    df = df[['timestamp_utc', 'wind_speed_mph', 'wind_direction_deg']].dropna(subset=['timestamp_utc'])

    # Resample to hourly mean (ISD has sub-hourly obs)
    df = (
        df.set_index('timestamp_utc')
        .resample('h')
        .mean()
        .reset_index()
    )

    print(f"  Wind KSAN {year}: {len(df)} rows")
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="Fetch one year of historical surf data")
    p.add_argument("--year", type=int, default=2024, help="Year to fetch (e.g. 2024)")
    p.add_argument("--out",  type=Path, default=None, help="Optional CSV output path")
    args = p.parse_args()

    print(f"\n=== Fetching {args.year} historical data ===\n")

    print("[1/3] Buoy")
    buoy = fetch_buoy_historical(args.year)

    print("\n[2/3] Tide")
    tide = fetch_tide_historical(args.year)

    print("\n[3/3] Wind (KSAN)")
    wind = fetch_wind_historical(args.year)

    print("\n=== Output shapes ===")
    print(f"Buoy : {buoy.shape}  columns: {list(buoy.columns)}")
    print(f"Tide : {tide.shape}  columns: {list(tide.columns)}")
    print(f"Wind : {wind.shape}  columns: {list(wind.columns)}")

    print("\n=== Buoy sample ===")
    print(buoy.head(3).to_string())

    print("\n=== Tide sample ===")
    print(tide.head(3).to_string())

    print("\n=== Wind sample ===")
    print(wind.head(3).to_string())

    if args.out:
        # Merge all three on hourly timestamp for a combined output
        buoy_h = buoy.copy()
        buoy_h['hour'] = buoy_h['timestamp_utc'].dt.floor('h')
        tide_h = tide.copy()
        tide_h['hour'] = tide_h['timestamp_utc'].dt.floor('h')
        wind_h = wind.copy()
        wind_h['hour'] = wind_h['timestamp_utc'].dt.floor('h')

        merged = (
            buoy_h.merge(tide_h[['hour', 'tide_height_m']], on='hour', how='left')
                  .merge(wind_h[['hour', 'wind_speed_mph', 'wind_direction_deg']], on='hour', how='left')
        )
        merged = merged.drop(columns='hour')
        args.out.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(args.out, index=False)
        print(f"\nWrote merged dataset → {args.out}  shape: {merged.shape}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
