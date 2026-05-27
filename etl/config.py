"""
Shared constants for Week 1 ETL.

Team: update notes here when you change station IDs, break coordinates, or paths.
"""

from __future__ import annotations

from pathlib import Path

# Repo root (parent of etl/)
REPO_ROOT = Path(__file__).resolve().parents[1]

# Cache raw downloads under data/raw/ (gitignored)
DATA_RAW = REPO_ROOT / "data" / "raw"
NDBC_CACHE_DIR = DATA_RAW / "ndbc"
NWS_CACHE_DIR = DATA_RAW / "nws"

# NDBC Standard Meteorological (stdmet) realtime2 feeds — verify columns in README if NOAA changes layout
NDBC_REALTIME2_URL = "https://www.ndbc.noaa.gov/data/realtime2/{station}.txt"
NDBC_STATIONS = (
    "46232",  # Point Loma South
    "46254",  # Mission Bay West
)

# Surf breaks — approximate coordinates for NWS grid lookup (api.weather.gov /points).
# Confirm on a map; if hourly returns 404 / marine-only issues, try a nearby inland proxy — ask mentor.
BREAKS: dict[str, tuple[float, float]] = {
    "la_jolla_shores": (32.8579, -117.2575),
    "blacks": (32.8807, -117.2436),
    "pb_point": (32.7970, -117.2550),
}

# NOAA CO-OPS tide station — 9410170 is La Jolla
TIDE_STATION = "9410170"
NOAA_TIDES_CACHE_DIR = DATA_RAW / "noaa_tides"

# NWS requires a descriptive User-Agent (identify your app / repo / contact).
# Replace with your club or mentor-approved string before heavy use.
NWS_USER_AGENT = (
    "SurfCastSD/0.1 (college club project; https://github.com/Igosain08/surfcastSD)"
)

# Surfline internal rating API cache directory
SURFLINE_CACHE_DIR = DATA_RAW / "surfline"

# Surfline spot IDs for each break — found from Surfline URLs
# e.g. surfline.com/surf-report/blacks/5842041f4e65fad6a770883b
SURFLINE_SPOT_IDS: dict[str, str] = {
    "la_jolla_shores": "5842041f4e65fad6a77088cc",
    "blacks":          "5842041f4e65fad6a770883b",
    "pb_point":        "5842041f4e65fad6a77088c2",
}