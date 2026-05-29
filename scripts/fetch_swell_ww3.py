#!/usr/bin/env python3
"""
WW3 swell fetcher — replaces Open-Meteo Marine for real APD/DPD separation.

Uses GFS Wave (WaveWatch III) wcoast 0.16° grid from NOMADS.
Downloads hourly GRIB2 files f001-f156, extracts at NDBC station coords.

Variables used:
  perpw → DPD (peak wave period from wave energy spectrum)
  mpts  → APD (mean period of total sea — genuinely != DPD)
  swh   → WVHT (significant wave height)
  dirpw → MWD (peak wave direction)

Run standalone:
    python scripts/fetch_swell_ww3.py
"""

from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

log = logging.getLogger(__name__)

NOMADS_BASE = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod"

NDBC_COORDS = {
    "46232": (32.5300, -117.4200),
    "46254": (32.8675, -117.2670),
}

# Forecast hours to fetch — hourly through 156h (~6.5 days)
FORECAST_HOURS = list(range(1, 157))


def get_latest_available_cycle() -> tuple[str, str]:
    """
    Return (date_str, cycle_str) for the most recently available GFS cycle.

    GFS runs at 00Z, 06Z, 12Z, 18Z. Each cycle takes ~3.5h to publish.
    We use a conservative 4h lag to ensure data is available.
    """
    now = datetime.now(timezone.utc)
    # Walk back through cycles until we find one that's had 4h to publish
    for hours_back in range(0, 24, 6):
        candidate = now - timedelta(hours=hours_back)
        cycle_hour = (candidate.hour // 6) * 6
        cycle_time = candidate.replace(
            hour=cycle_hour, minute=0, second=0, microsecond=0
        )
        age_hours = (now - cycle_time).total_seconds() / 3600
        if age_hours >= 4:
            return cycle_time.strftime("%Y%m%d"), f"{cycle_hour:02d}"

    # Fallback to yesterday's 18Z
    yesterday = now - timedelta(days=1)
    return yesterday.strftime("%Y%m%d"), "18"


def build_url(date_str: str, cycle: str, fhour: int) -> str:
    filename = f"gfswave.t{cycle}z.wcoast.0p16.f{fhour:03d}.grib2"
    return f"{NOMADS_BASE}/gfs.{date_str}/{cycle}/wave/gridded/{filename}"


def download_grib(url: str) -> Path:
    """Download a GRIB2 file to a temp location."""
    resp = requests.get(url, timeout=30, stream=True)
    resp.raise_for_status()
    tmp = Path(tempfile.mktemp(suffix=".grib2"))
    with open(tmp, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
    return tmp


def extract_station_values(grib_path: Path) -> dict[str, dict[str, float]]:
    """
    Extract perpw, mpts, swh, dirpw at each NDBC station from one GRIB2 file.
    Returns {station_id: {variable: value}}.
    """
    import cfgrib

    results = {sid: {} for sid in NDBC_COORDS}

    try:
        datasets = cfgrib.open_datasets(str(grib_path))
    except Exception as e:
        log.warning("cfgrib failed to open %s: %s", grib_path, e)
        return results

    for ds in datasets:
        for var in ds.data_vars:
            if var not in ("perpw", "mpts", "swh", "dirpw"):
                continue
            try:
                da = ds[var]
                lat_arr = da.latitude.values
                lon_arr = da.longitude.values

                for station, (lat, lon) in NDBC_COORDS.items():
                    lon_360 = lon % 360
                    lat_idx = int(np.argmin(np.abs(lat_arr - lat)))
                    lon_idx = int(np.argmin(np.abs(lon_arr - lon_360)))

                    if da.values.ndim == 2:
                        val = float(da.values[lat_idx, lon_idx])
                    elif da.values.ndim == 3:
                        # Swell partitions — take partition 0 (dominant)
                        val = float(da.values[0, lat_idx, lon_idx])
                    else:
                        continue

                    # Skip fill values (WW3 uses 9999 for missing)
                    if not np.isnan(val) and abs(val) < 9000:
                        results[station][var] = val

            except Exception as e:
                log.debug("Could not extract %s: %s", var, e)

    return results


def fetch_swell_ww3(forecast_hours: list[int] = FORECAST_HOURS) -> pd.DataFrame:
    """
    Fetch WW3 swell forecast for all NDBC stations.
    Returns long-format DataFrame with columns:
      timestamp_utc, station, WVHT, DPD, MWD, APD
    """
    date_str, cycle = get_latest_available_cycle()
    cycle_time = datetime.strptime(
        f"{date_str} {cycle}:00", "%Y%m%d %H:%M"
    ).replace(tzinfo=timezone.utc)

    log.info("Using GFS Wave cycle: %sZ %s", date_str, cycle)

    rows = []
    total = len(forecast_hours)

    for i, fhour in enumerate(forecast_hours):
        url = build_url(date_str, cycle, fhour)
        timestamp = cycle_time + timedelta(hours=fhour)

        # Progress every 10 files
        if i % 10 == 0:
            log.info("Fetching hour %d/%d (f%03d)...", i + 1, total, fhour)

        try:
            grib_path = download_grib(url)
        except requests.RequestException as e:
            log.warning("Download failed for f%03d: %s — skipping", fhour, e)
            continue

        try:
            station_values = extract_station_values(grib_path)
        finally:
            # Always delete temp file even if extraction fails
            grib_path.unlink(missing_ok=True)

        for station, vals in station_values.items():
            rows.append({
                "timestamp_utc": pd.Timestamp(timestamp).floor("h"),
                "station": station,
                "WVHT": vals.get("swh", np.nan),
                "DPD": vals.get("perpw", np.nan),
                "MWD": vals.get("dirpw", np.nan),
                "APD": vals.get("mpts", np.nan),
            })

    if not rows:
        log.error("No WW3 data fetched — all hours failed")
        return pd.DataFrame(
            columns=["timestamp_utc", "station", "WVHT", "DPD", "MWD", "APD"]
        )

    df = pd.DataFrame(rows)
    log.info(
        "WW3 fetch complete: %d rows, APD/DPD gap avg: %.2fs",
        len(df),
        (df["DPD"] - df["APD"]).mean(),
    )
    return df


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Test with just first 5 hours to verify before running all 156
    log.info("Testing with first 5 forecast hours...")
    df = fetch_swell_ww3(forecast_hours=list(range(1, 6)))

    print("\nShape:", df.shape)
    print("\nSample:")
    print(df.to_string())
    print("\nAPD vs DPD:")
    print(df[["station", "DPD", "APD"]].to_string())
    print(f"\nMean DPD-APD gap: {(df['DPD'] - df['APD']).mean():.3f}s")
    print(f"Min gap: {(df['DPD'] - df['APD']).min():.3f}s")
    print(f"Max gap: {(df['DPD'] - df['APD']).max():.3f}s")


if __name__ == "__main__":
    main()