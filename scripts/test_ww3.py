#!/usr/bin/env python3
"""
Test script — verify GFS Wave WW3 data access for San Diego NDBC stations.
Downloads one hour of wcoast grid data and extracts PERPW (DPD) and WVPER (APD)
at station coordinates.

Run from repo root:
    python scripts/test_ww3.py
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests

# NDBC station coordinates
NDBC_COORDS = {
    "46232": (32.5300, -117.4200),  # Point Loma South
    "46254": (32.8675, -117.2670),  # Mission Bay West
}

NOMADS_BASE = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod"


def get_latest_cycle() -> tuple[str, str]:
    """Return (date_str, cycle_str) for the most recently available 06Z cycle."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d")
    # Use 06Z — reliably available by afternoon UTC
    return date_str, "06"


def download_wcoast_file(date_str: str, cycle: str, fhour: int) -> Path:
    """Download one wcoast GRIB2 file to a temp location and return the path."""
    filename = f"gfswave.t{cycle}z.wcoast.0p16.f{fhour:03d}.grib2"
    url = f"{NOMADS_BASE}/gfs.{date_str}/{cycle}/wave/gridded/{filename}"

    print(f"Downloading: {url}")
    resp = requests.get(url, timeout=30, stream=True)
    resp.raise_for_status()

    tmp = Path(tempfile.mktemp(suffix=".grib2"))
    with open(tmp, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded {tmp.stat().st_size / 1024:.1f} KB to {tmp}")
    return tmp


def extract_at_coords(grib_path: Path, lat: float, lon: float) -> dict:
    """Extract wave variables at nearest gridpoint to (lat, lon)."""
    import cfgrib

    lon_360 = lon % 360
    results = {}

    datasets = cfgrib.open_datasets(str(grib_path))
    print(f"\nFound {len(datasets)} variable groups in GRIB2 file:")

    for ds in datasets:
        print(f"  Variables: {list(ds.data_vars)}")
        for var in ds.data_vars:
            try:
                da = ds[var]

                # Handle multi-dimensional arrays (e.g. swell partitions)
                # lat/lon are always the last two dims
                if da.values.ndim == 2:
                    lat_arr = da.latitude.values
                    lon_arr = da.longitude.values
                    lat_idx = int(np.argmin(np.abs(lat_arr - lat)))
                    lon_idx = int(np.argmin(np.abs(lon_arr - lon_360)))
                    val = float(da.values[lat_idx, lon_idx])
                elif da.values.ndim == 3:
                    # First dim is partition (e.g. swell 1/2/3)
                    # Take partition 0 (dominant swell)
                    lat_arr = da.latitude.values
                    lon_arr = da.longitude.values
                    lat_idx = int(np.argmin(np.abs(lat_arr - lat)))
                    lon_idx = int(np.argmin(np.abs(lon_arr - lon_360)))
                    val = float(da.values[0, lat_idx, lon_idx])
                else:
                    print(f"    {var}: unexpected shape {da.values.shape} — skipping")
                    continue

                results[var] = val
                print(f"    {var}: {val:.3f}")
            except Exception as e:
                print(f"    {var}: could not extract — {e}")

    return results


def main() -> None:
    print("=== GFS Wave WW3 Test ===\n")

    date_str, cycle = get_latest_cycle()
    print(f"Using cycle: {date_str} {cycle}Z\n")

    # Download just the first forecast hour (f001) as a test
    try:
        grib_path = download_wcoast_file(date_str, cycle, fhour=1)
    except requests.RequestException as e:
        print(f"Download failed: {e}")
        return

    # Extract at each NDBC station
    for station, (lat, lon) in NDBC_COORDS.items():
        print(f"\n--- Station {station} at ({lat}, {lon}) ---")
        try:
            result = extract_at_coords(grib_path, lat, lon)
            print(f"\nKey variables for station {station}:")
            for key in ["perpw", "mpww", "mpts", "swh", "shts", "dirpw", "wvdir"]:
                if key in result:
                    print(f"  {key}: {result[key]:.3f}")
                else:
                    print(f"  {key}: not found")
        except Exception as e:
            print(f"Extraction failed: {e}")

    # Clean up
    grib_path.unlink(missing_ok=True)
    print("\n=== Done ===")


if __name__ == "__main__":
    main()