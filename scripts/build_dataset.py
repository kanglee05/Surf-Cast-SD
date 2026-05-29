#!/usr/bin/env python3
"""
Full pipeline — builds training_set_without_labels.csv from raw sources.

Steps:
  1. Fetch buoy data     (NDBC stations 46232 + 46254, cached under data/raw/ndbc_historical/)
  2. Fetch tide data     (NOAA CO-OPS station 9410170, cached under data/raw/noaa_tides/historical/)
  3. Fetch wind data     (KSAN ISD, cached under data/raw/isd_wind/KSAN_YYYY.csv)
  4. Merge all three on hourly timestamp
  5. Add astral season features  (day_length_hours, sunrise/sunset, hours_since_sunrise, season_sin/cos)
  6. Add KSAN weather features   (temp_c, humidity_pct from same ISD files)

No Surfline token needed. Anyone on the team can run this once.

Run from repo root:
    python scripts/build_dataset.py
    python scripts/build_dataset.py --years 2022 2023 2024
    python scripts/build_dataset.py --out data/processed/my_features.csv

Output: data/processed/training_set_without_labels.csv

To add Surfline labels on top (requires SURFLINE_ACCESS_TOKEN):
    export SURFLINE_ACCESS_TOKEN="your_token"
    python -m etl.fetch_labels --historical --out data/processed/surfline_labels.csv
    python scripts/build_training_set.py --features data/processed/training_set_without_labels.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytz
from astral import LocationInfo
from astral.sun import sun

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.fetch_historical_data_yearly import (
    fetch_buoy_historical,
    fetch_tide_historical,
    fetch_wind_historical,
)
from etl.config import DATA_RAW

SD  = LocationInfo("San Diego", "USA", "America/Los_Angeles", 32.7157, -117.1611)
UTC = pytz.utc


# ---------------------------------------------------------------------------
# Step 1-3 — Fetch and merge raw buoy / tide / wind
# ---------------------------------------------------------------------------

def fetch_and_merge(years: list[int]) -> pd.DataFrame:
    buoy_frames, tide_frames, wind_frames = [], [], []

    for year in years:
        print(f"  [{year}] Fetching buoy (NDBC)...")
        buoy_frames.append(fetch_buoy_historical(year))

        print(f"  [{year}] Fetching tide (NOAA CO-OPS)...")
        tide_frames.append(fetch_tide_historical(year))

        print(f"  [{year}] Fetching wind (KSAN ISD)...")
        wind_frames.append(fetch_wind_historical(year))

    buoy = pd.concat(buoy_frames, ignore_index=True).sort_values("timestamp_utc")
    tide = pd.concat(tide_frames, ignore_index=True).sort_values("timestamp_utc")
    wind = pd.concat(wind_frames, ignore_index=True).sort_values("timestamp_utc")

    buoy["_hour"] = buoy["timestamp_utc"].dt.floor("h")
    tide["_hour"] = tide["timestamp_utc"].dt.floor("h")
    wind["_hour"] = wind["timestamp_utc"].dt.floor("h")

    merged = (
        buoy.merge(tide[["_hour", "tide_height_m"]], on="_hour", how="left")
            .merge(wind[["_hour", "wind_speed_mph", "wind_direction_deg"]], on="_hour", how="left")
    )
    merged = merged.drop(columns="_hour")
    print(f"  Merged shape: {merged.shape}")
    return merged


# ---------------------------------------------------------------------------
# Step 4 — Astral season features
# ---------------------------------------------------------------------------

def add_astral_features(df: pd.DataFrame) -> pd.DataFrame:
    print("  Computing sunrise/sunset for all unique dates...")
    df = df.copy()
    df["_date"]     = df["timestamp_utc"].dt.date
    df["_hour_utc"] = df["timestamp_utc"].dt.hour + df["timestamp_utc"].dt.minute / 60

    cache = {}
    for d in df["_date"].unique():
        try:
            s    = sun(SD.observer, date=d, tzinfo=SD.timezone)
            rise = s["sunrise"].astimezone(UTC)
            sset = s["sunset"].astimezone(UTC)
            day_len = (sset - rise).total_seconds() / 3600
            cache[d] = (rise.hour + rise.minute / 60, sset.hour + sset.minute / 60, day_len)
        except Exception:
            cache[d] = (6.5, 18.5, 12.0)

    df["sunrise_hour_utc"]    = df["_date"].map(lambda d: cache[d][0])
    df["sunset_hour_utc"]     = df["_date"].map(lambda d: cache[d][1])
    df["day_length_hours"]    = df["_date"].map(lambda d: cache[d][2])
    df["hours_since_sunrise"] = (df["_hour_utc"] - df["sunrise_hour_utc"]).clip(lower=0)

    doy              = df["timestamp_utc"].dt.day_of_year
    df["season_sin"] = np.sin(2 * np.pi * doy / 365)
    df["season_cos"] = np.cos(2 * np.pi * doy / 365)

    df.drop(columns=["_date", "_hour_utc"], inplace=True)
    print("  Added: sunrise_hour_utc, sunset_hour_utc, day_length_hours, hours_since_sunrise, season_sin, season_cos")
    return df


# ---------------------------------------------------------------------------
# Step 5 — KSAN weather features (temp_c, humidity_pct)
# ---------------------------------------------------------------------------

def parse_isd_temp(s) -> float:
    try:
        val = float(str(s).split(",")[0]) / 10
        return np.nan if abs(val) >= 999 else val
    except Exception:
        return np.nan


def add_weather_features(df: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    isd_dir = DATA_RAW / "isd_wind"
    frames  = []

    for year in sorted(years):
        path = isd_dir / f"KSAN_{year}.csv"
        if not path.exists():
            print(f"  Warning: KSAN_{year}.csv not found — skipping")
            continue
        raw = pd.read_csv(path, low_memory=False)
        raw["timestamp_utc"] = pd.to_datetime(raw["DATE"], utc=True, errors="coerce")
        raw["temp_c"]        = raw["TMP"].apply(parse_isd_temp)
        raw["dewp_c"]        = raw["DEW"].apply(parse_isd_temp)
        num = np.exp((17.625 * raw["dewp_c"]) / (243.04 + raw["dewp_c"]))
        den = np.exp((17.625 * raw["temp_c"])  / (243.04 + raw["temp_c"]))
        raw["humidity_pct"] = (100 * num / den).clip(0, 100)
        out    = raw[["timestamp_utc", "temp_c", "humidity_pct"]].dropna(subset=["timestamp_utc"])
        hourly = out.set_index("timestamp_utc").resample("h").mean().reset_index()
        frames.append(hourly)
        print(f"  KSAN {year}: {len(hourly)} hourly weather rows")

    if not frames:
        print("  No KSAN files found — skipping weather features")
        return df

    weather = pd.concat(frames, ignore_index=True)
    weather["timestamp_utc"] = weather["timestamp_utc"].dt.floor("h")

    df = df.copy()
    df["_ts"] = df["timestamp_utc"].dt.floor("h")
    df = df.merge(weather, left_on="_ts", right_on="timestamp_utc",
                  how="left", suffixes=("", "_w"))
    df.drop(columns=["_ts", "timestamp_utc_w"], inplace=True, errors="ignore")
    print(f"  temp_c missing: {df['temp_c'].isnull().sum()} ({df['temp_c'].isnull().mean()*100:.1f}%)")
    print("  Added: temp_c, humidity_pct")
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="Build full feature dataset (no Surfline labels needed)")
    p.add_argument("--years", nargs="+", type=int, default=[2022, 2023, 2024],
                   help="Years to include (default: 2022 2023 2024)")
    p.add_argument("--out", type=Path,
                   default=ROOT / "data/processed/training_set_without_labels.csv",
                   help="Output CSV path")
    args = p.parse_args()

    print(f"\n=== SurfCast SD — Build Dataset (no labels) for {args.years} ===\n")

    print("[1/3] Fetching and merging raw buoy / tide / wind data...")
    df = fetch_and_merge(args.years)

    print("\n[2/3] Adding astral season features...")
    df = add_astral_features(df)

    print("\n[3/3] Adding KSAN weather features (temp, humidity)...")
    df = add_weather_features(df, args.years)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)

    print(f"\n=== Done ===")
    print(f"Rows:    {len(df):,}")
    print(f"Columns: {list(df.columns)}")
    print(f"Saved  → {args.out}")
    print(f"\nTo add Surfline labels:")
    print(f"  export SURFLINE_ACCESS_TOKEN='your_token'")
    print(f"  python -m etl.fetch_labels --historical --out data/processed/surfline_labels.csv")
    print(f"  python scripts/build_training_set.py --features {args.out}")


if __name__ == "__main__":
    main()
