#!/usr/bin/env python3
"""
Enrich training_set.csv with:
  1. Astral season features  — day_length_hours, hours_since_sunrise, season_sin, season_cos
  2. KSAN weather features   — temp_c, humidity_pct (from ISD files already downloaded)

Run from repo root:
    python scripts/enrich_training_set.py

Output: data/processed/training_set_enriched.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytz
from astral import LocationInfo
from astral.sun import sun
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TRAINING_SET  = ROOT / "data/processed/training_set.csv"
ISD_DIR       = ROOT / "data/raw/isd_wind"
OUT_PATH      = ROOT / "data/processed/training_set_enriched.csv"

SD = LocationInfo("San Diego", "USA", "America/Los_Angeles", 32.7157, -117.1611)
UTC = pytz.utc


# ---------------------------------------------------------------------------
# 1. Astral season features
# ---------------------------------------------------------------------------

def compute_sun_cache(dates: list[date]) -> dict:
    """Return {date: (sunrise_hour_utc, sunset_hour_utc, day_length_hours)}."""
    cache = {}
    for d in dates:
        try:
            s = sun(SD.observer, date=d, tzinfo=SD.timezone)
            rise = s["sunrise"].astimezone(UTC)
            sset = s["sunset"].astimezone(UTC)
            day_len = (sset - rise).total_seconds() / 3600
            cache[d] = (rise.hour + rise.minute / 60, sset.hour + sset.minute / 60, day_len)
        except Exception:
            cache[d] = (6.5, 18.5, 12.0)
    return cache


def add_astral_features(df: pd.DataFrame) -> pd.DataFrame:
    print("  Computing sunrise/sunset for all dates via astral...")
    df = df.copy()
    df["_date"] = df["timestamp_utc"].dt.date
    df["_hour_utc"] = df["timestamp_utc"].dt.hour + df["timestamp_utc"].dt.minute / 60

    cache = compute_sun_cache(df["_date"].unique().tolist())

    df["sunrise_hour_utc"]    = df["_date"].map(lambda d: cache[d][0])
    df["sunset_hour_utc"]     = df["_date"].map(lambda d: cache[d][1])
    df["day_length_hours"]    = df["_date"].map(lambda d: cache[d][2])
    df["hours_since_sunrise"] = (df["_hour_utc"] - df["sunrise_hour_utc"]).clip(lower=0)

    doy = df["timestamp_utc"].dt.day_of_year
    df["season_sin"] = np.sin(2 * np.pi * doy / 365)
    df["season_cos"] = np.cos(2 * np.pi * doy / 365)

    df.drop(columns=["_date", "_hour_utc"], inplace=True)
    print(f"  Astral features added: day_length_hours, hours_since_sunrise, season_sin, season_cos")
    return df


# ---------------------------------------------------------------------------
# 2. KSAN weather features
# ---------------------------------------------------------------------------

def parse_isd_temp(s) -> float:
    """Parse ISD TMP/DEW field '+0161,1' → 16.1°C."""
    try:
        val = float(str(s).split(",")[0]) / 10
        return np.nan if abs(val) >= 999 else val
    except Exception:
        return np.nan


def relative_humidity(temp_c: pd.Series, dewp_c: pd.Series) -> pd.Series:
    """Magnus formula: RH from temperature and dewpoint."""
    num = np.exp((17.625 * dewp_c) / (243.04 + dewp_c))
    den = np.exp((17.625 * temp_c) / (243.04 + temp_c))
    return (100 * num / den).clip(0, 100)


def load_ksan_weather(years: list[int]) -> pd.DataFrame:
    frames = []
    for year in years:
        path = ISD_DIR / f"KSAN_{year}.csv"
        if not path.exists():
            print(f"  Warning: {path.name} not found — skipping {year}")
            continue
        raw = pd.read_csv(path, low_memory=False)
        raw["timestamp_utc"] = pd.to_datetime(raw["DATE"], utc=True, errors="coerce")
        raw["temp_c"] = raw["TMP"].apply(parse_isd_temp)
        raw["dewp_c"] = raw["DEW"].apply(parse_isd_temp)
        raw["humidity_pct"] = relative_humidity(raw["temp_c"], raw["dewp_c"])
        out = raw[["timestamp_utc", "temp_c", "humidity_pct"]].dropna(subset=["timestamp_utc"])
        hourly = out.set_index("timestamp_utc").resample("h").mean().reset_index()
        frames.append(hourly)
        print(f"  KSAN {year}: {len(hourly)} hourly rows")
    return pd.concat(frames, ignore_index=True)


def add_weather_features(df: pd.DataFrame) -> pd.DataFrame:
    print("  Loading KSAN temperature and humidity...")
    weather = load_ksan_weather([2022, 2023, 2024])
    weather["timestamp_utc"] = weather["timestamp_utc"].dt.floor("h")

    df = df.copy()
    df["_merge_ts"] = df["timestamp_utc"].dt.floor("h")
    df = df.merge(weather, left_on="_merge_ts", right_on="timestamp_utc",
                  how="left", suffixes=("", "_w"))
    df.drop(columns=["_merge_ts", "timestamp_utc_w"], inplace=True, errors="ignore")

    missing_temp = df["temp_c"].isnull().sum()
    missing_hum  = df["humidity_pct"].isnull().sum()
    print(f"  temp_c missing: {missing_temp} ({missing_temp/len(df)*100:.1f}%)")
    print(f"  humidity_pct missing: {missing_hum} ({missing_hum/len(df)*100:.1f}%)")
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"\n=== Enriching training set ===")
    print(f"Input:  {TRAINING_SET}")

    print("\n[1/3] Loading training set...")
    df = pd.read_csv(TRAINING_SET, parse_dates=["timestamp_utc"])
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    print(f"  Loaded {len(df):,} rows × {df.shape[1]} columns")

    print("\n[2/3] Adding astral season features...")
    df = add_astral_features(df)

    print("\n[3/3] Adding KSAN weather features...")
    df = add_weather_features(df)

    print(f"\n=== Saving enriched dataset ===")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)

    print(f"  Rows:    {len(df):,}")
    print(f"  Columns: {df.shape[1]}")
    print(f"  New features: {['day_length_hours','hours_since_sunrise','season_sin','season_cos','sunrise_hour_utc','sunset_hour_utc','temp_c','humidity_pct']}")
    print(f"\nSaved → {OUT_PATH}")
    print("\nColumn list:")
    print(list(df.columns))


if __name__ == "__main__":
    main()
