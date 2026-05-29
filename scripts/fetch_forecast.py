#!/usr/bin/env python3
"""
Daily 7-day forecast pipeline — outputs forecast_<YYYYMMDD>.csv to GCS.

Matches training_set_enriched schema (minus labels):
  timestamp_utc, station, WVHT, DPD, MWD, APD, tide_height_m,
  wind_speed_mph, wind_direction_deg, break_id,
  sunrise_hour_utc, sunset_hour_utc, day_length_hours, hours_since_sunrise,
  season_sin, season_cos, temp_c, humidity_pct

Sources:
  - Wind:     NWS forecast/hourly per break
  - Tide:     NOAA CO-OPS predictions (station 9410170, La Jolla)
  - Swell:    Open-Meteo Marine API per NDBC station coords
  - Weather:  Open-Meteo Weather API (temp, humidity)
  - Astral:   astral library (sunrise/sunset/season)

Output: 6 rows per hourly timestamp (2 stations × 3 breaks), 7 days = ~1008 rows/day.

Run locally:
    python -m scripts.fetch_forecast

Deployed to Cloud Run, triggered daily by Cloud Scheduler at 13:00 UTC.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytz
import requests
from astral import LocationInfo
from astral.sun import sun
from google.cloud import storage

from etl.config import BREAKS, NDBC_STATIONS, NWS_USER_AGENT, TIDE_STATION

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# San Diego location for astral
SD = LocationInfo("San Diego", "USA", "America/Los_Angeles", 32.7157, -117.1611)
UTC = pytz.utc

# NDBC station coordinates (for Open-Meteo Marine lookup)
NDBC_COORDS = {
    "46232": (32.5300, -117.4200),  # Point Loma South
    "46254": (32.8675, -117.2670),  # Mission Bay West
}

# Compass-to-degrees for NWS wind direction
COMPASS_TO_DEGREES = {
    "N": 0, "NNE": 22, "NE": 45, "ENE": 67,
    "E": 90, "ESE": 112, "SE": 135, "SSE": 157,
    "S": 180, "SSW": 202, "SW": 225, "WSW": 247,
    "W": 270, "WNW": 292, "NW": 315, "NNW": 337,
}

FORECAST_DAYS = 7


# ---------------------------------------------------------------------------
# Wind — NWS forecast/hourly per break
# ---------------------------------------------------------------------------

def parse_wind_speed(speed_str: str) -> float:
    """Parse NWS wind speed string to mph. Handles 'Calm', '5 mph', '5 to 10 mph'."""
    if not speed_str or speed_str.strip().lower() == "calm":
        return 0.0
    numbers = re.findall(r"\d+(?:\.\d+)?", speed_str)
    if not numbers:
        return 0.0
    return float(max(numbers, key=float))


def fetch_wind_forecast() -> pd.DataFrame:
    """Return long-format wind forecast per break."""
    headers = {"User-Agent": NWS_USER_AGENT, "Accept": "application/geo+json"}
    rows = []

    for break_id, (lat, lon) in BREAKS.items():
        try:
            points = requests.get(
                f"https://api.weather.gov/points/{lat},{lon}",
                headers=headers, timeout=15,
            )
            points.raise_for_status()
            hourly_url = points.json()["properties"].get("forecastHourly")
            if not hourly_url:
                log.warning("No forecastHourly for %s — skipping", break_id)
                continue

            forecast = requests.get(hourly_url, headers=headers, timeout=15)
            forecast.raise_for_status()
            periods = forecast.json()["properties"]["periods"]
        except requests.RequestException as e:
            log.warning("Wind fetch failed for %s: %s", break_id, e)
            continue

        for p in periods:
            rows.append({
                "timestamp_utc": pd.Timestamp(p["startTime"]).tz_convert("UTC").floor("h"),
                "break_id": break_id,
                "wind_speed_mph": parse_wind_speed(p.get("windSpeed", "")),
                "wind_direction_deg": COMPASS_TO_DEGREES.get(
    p.get("windDirection", "N").upper(), 0
),
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tide — NOAA CO-OPS predictions
# ---------------------------------------------------------------------------

def fetch_tide_forecast(days: int = FORECAST_DAYS) -> pd.DataFrame:
    """Return hourly tide predictions for the next N days."""
    begin = datetime.now(timezone.utc).strftime("%Y%m%d")
    end = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y%m%d")

    url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    params = {
        "product": "predictions",
        "application": "SurfCastSD",
        "station": TIDE_STATION,
        "begin_date": begin,
        "end_date": end,
        "datum": "MLLW",
        "time_zone": "gmt",
        "interval": "h",
        "units": "metric",
        "format": "json",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        preds = resp.json().get("predictions", [])
    except requests.RequestException as e:
        log.warning("Tide fetch failed: %s", e)
        return pd.DataFrame(columns=["timestamp_utc", "tide_height_m"])

    rows = [
        {
            "timestamp_utc": pd.Timestamp(p["t"], tz="UTC").floor("h"),
            "tide_height_m": float(p["v"]),
        }
        for p in preds
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Swell — Open-Meteo Marine API per NDBC station
# ---------------------------------------------------------------------------

def fetch_swell_forecast(days: int = FORECAST_DAYS) -> pd.DataFrame:
    """Return swell forecast per station: WVHT, DPD, MWD, APD."""
    rows = []
    for station, (lat, lon) in NDBC_COORDS.items():
        url = "https://marine-api.open-meteo.com/v1/marine"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "wave_height,wave_direction,wave_period",
            "forecast_days": days,
            "timezone": "UTC",
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json().get("hourly", {})
        except requests.RequestException as e:
            log.warning("Swell fetch failed for station %s: %s", station, e)
            continue

        times = data.get("time", [])
        wvht = data.get("wave_height", [])
        mwd = data.get("wave_direction", [])
        period = data.get("wave_period", [])

        for i, t in enumerate(times):
            rows.append({
                "timestamp_utc": pd.Timestamp(t, tz="UTC").floor("h"),
                "station": station,
                "WVHT": wvht[i] if i < len(wvht) else np.nan,
                "DPD": period[i] if i < len(period) else np.nan,
                "MWD": mwd[i] if i < len(mwd) else np.nan,
                "APD": period[i] if i < len(period) else np.nan,  # Open-Meteo gives one period
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Weather — Open-Meteo Weather API (San Diego, temp + humidity)
# ---------------------------------------------------------------------------

def fetch_weather_forecast(days: int = FORECAST_DAYS) -> pd.DataFrame:
    """Return hourly temp and humidity for San Diego."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 32.7157,
        "longitude": -117.1611,
        "hourly": "temperature_2m,relative_humidity_2m",
        "forecast_days": days,
        "timezone": "UTC",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("hourly", {})
    except requests.RequestException as e:
        log.warning("Weather fetch failed: %s", e)
        return pd.DataFrame(columns=["timestamp_utc", "temp_c", "humidity_pct"])

    times = data.get("time", [])
    temps = data.get("temperature_2m", [])
    rh = data.get("relative_humidity_2m", [])

    rows = [
        {
            "timestamp_utc": pd.Timestamp(t, tz="UTC").floor("h"),
            "temp_c": temps[i] if i < len(temps) else np.nan,
            "humidity_pct": rh[i] if i < len(rh) else np.nan,
        }
        for i, t in enumerate(times)
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Astral features (sunrise/sunset/season) — pure computation
# ---------------------------------------------------------------------------

def add_astral_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_date"] = df["timestamp_utc"].dt.date
    df["_hour_utc"] = df["timestamp_utc"].dt.hour + df["timestamp_utc"].dt.minute / 60

    cache = {}
    for d in df["_date"].unique():
        try:
            s = sun(SD.observer, date=d, tzinfo=SD.timezone)
            rise = s["sunrise"].astimezone(UTC)
            sset = s["sunset"].astimezone(UTC)
            day_len = (sset - rise).total_seconds() / 3600
            cache[d] = (
                rise.hour + rise.minute / 60,
                sset.hour + sset.minute / 60,
                day_len,
            )
        except Exception:
            cache[d] = (6.5, 18.5, 12.0)

    df["sunrise_hour_utc"] = df["_date"].map(lambda d: cache[d][0])
    df["sunset_hour_utc"] = df["_date"].map(lambda d: cache[d][1])
    df["day_length_hours"] = df["_date"].map(lambda d: cache[d][2])
    df["hours_since_sunrise"] = (df["_hour_utc"] - df["sunrise_hour_utc"]).clip(lower=0)

    doy = df["timestamp_utc"].dt.day_of_year
    df["season_sin"] = np.sin(2 * np.pi * doy / 365)
    df["season_cos"] = np.cos(2 * np.pi * doy / 365)

    df.drop(columns=["_date", "_hour_utc"], inplace=True)
    return df


# ---------------------------------------------------------------------------
# Assemble — cross-product into full schema
# ---------------------------------------------------------------------------

def build_forecast_dataset() -> pd.DataFrame:
    log.info("Fetching wind forecast...")
    wind = fetch_wind_forecast()

    log.info("Fetching tide forecast...")
    tide = fetch_tide_forecast()

    log.info("Fetching swell forecast...")
    swell = fetch_swell_forecast()

    log.info("Fetching weather forecast...")
    weather = fetch_weather_forecast()

    if swell.empty or wind.empty:
        log.error("Missing wind or swell data — cannot build dataset")
        return pd.DataFrame()

    # Clip forecast window to NWS coverage (shortest of the APIs ~156h)
    # so every row has wind data; avoids trailing NaNs from longer-range APIs.
    wind_max = wind["timestamp_utc"].max()
    wind_min = wind["timestamp_utc"].min()
    log.info("Clipping forecast window to NWS range: %s → %s", wind_min, wind_max)

    swell = swell[(swell["timestamp_utc"] >= wind_min) & (swell["timestamp_utc"] <= wind_max)].copy()
    tide = tide[(tide["timestamp_utc"] >= wind_min) & (tide["timestamp_utc"] <= wind_max)].copy()
    weather = weather[(weather["timestamp_utc"] >= wind_min) & (weather["timestamp_utc"] <= wind_max)].copy()

    # Start from swell (it has both timestamp and station)
    df = swell.copy()

    # Cross-product with breaks: each (timestamp, station) gets 3 rows for 3 breaks
    breaks_df = pd.DataFrame({"break_id": list(BREAKS.keys())})
    df = df.merge(breaks_df, how="cross")

    # Merge wind (per break)
    df = df.merge(wind, on=["timestamp_utc", "break_id"], how="left")

    # Merge tide (single station, all rows)
    df = df.merge(tide, on="timestamp_utc", how="left")

    # Merge weather (single location, all rows)
    df = df.merge(weather, on="timestamp_utc", how="left")

    # Add astral features
    df = add_astral_features(df)

    # Reorder columns to match training_set_enriched (minus labels)
    column_order = [
        "timestamp_utc", "station", "WVHT", "DPD", "MWD", "APD",
        "tide_height_m", "wind_speed_mph", "wind_direction_deg", "break_id",
        "sunrise_hour_utc", "sunset_hour_utc", "day_length_hours",
        "hours_since_sunrise", "season_sin", "season_cos",
        "temp_c", "humidity_pct",
    ]
    df = df[column_order].sort_values(["timestamp_utc", "station", "break_id"]).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Upload to GCS
# ---------------------------------------------------------------------------

def upload_to_gcs(df: pd.DataFrame) -> None:
    run_date = pd.Timestamp.now(tz="UTC").strftime("%Y%m%d")
    blob_name = f"forecast_{run_date}.csv"
    csv_data = df.to_csv(index=False)

    bucket_name = os.environ.get("GCS_BUCKET", "surfcast-sd-wind")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(csv_data, content_type="text/csv")
    log.info("Uploaded gs://%s/%s (%d rows)", bucket_name, blob_name, len(df))


def main() -> None:
    df = build_forecast_dataset()
    if df.empty:
        log.error("Empty dataset — nothing to upload")
        return
    log.info("Built dataset: %d rows, %d columns", len(df), len(df.columns))
    print(df.head())
    upload_to_gcs(df)


if __name__ == "__main__":
    main()