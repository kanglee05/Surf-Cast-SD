"""
Week 1 — Buoy ETL (your team implements this file)

Goal
----
Download NDBC **stdmet realtime2** text for stations **46232** (Point Loma South) and **46254**
(Mission Bay West), **cache** the raw `.txt` under ``data/raw/ndbc/``, parse into a **pandas**
DataFrame.

Output contract (``fetch_buoy_swell``)
--------------------------------------
Return one DataFrame (all stations concatenated) with at least:

- ``timestamp_utc`` — timezone-aware UTC (use ``pd.Timestamp`` with ``tz`` or ``utc=True``)
- ``station`` — string, e.g. ``"46232"``
- ``WVHT``, ``DPD``, ``MWD``, ``APD`` — numeric where possible (NDBC uses ``MM`` / sentinels for missing)

Filter to roughly the **last ``days``** of rows (based on timestamps in the file).

Hints
-----
- Feed URL pattern is in ``etl/config.NDBC_REALTIME2_URL`` / ``NDBC_STATIONS``.
- File format: comment lines start with ``#``; the **column header** line also starts with ``#``
  and begins with ``YY`` or ``YYYY``. Data rows may use **4-digit years** even when the header
  says ``YY``.
- Parse carefully: buoy data can have gaps; decide how you handle missing rows (document in PR).

References
----------
- https://www.ndbc.noaa.gov/measdes.shtml
- https://www.ndbc.noaa.gov/faq/stdmet.shtml (stdmet)

Checklist before opening a PR
-----------------------------
- [ ] Raw files cached locally under ``data/raw/ndbc/`` (paths in ``.gitignore`` / README — do not commit huge caches unless mentor says so)
- [ ] ``python -m etl.fetch_buoy`` prints a sensible ``head()`` when run from repo root
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import urllib.request

from etl.config import NDBC_CACHE_DIR, NDBC_STATIONS, NDBC_REALTIME2_URL


def download_station_txt(station: str, cache_dir: Path | None = None) -> Path:
    """Download realtime2 stdmet for ``station`` and save under ``cache_dir`` (default: ``NDBC_CACHE_DIR``)."""
    if cache_dir is None:
        cache_dir = NDBC_CACHE_DIR

    cache_dir.mkdir(parents=True, exist_ok=True)
    file_path = cache_dir / f"{station}.txt"
    url = NDBC_REALTIME2_URL.format(station=station)

    urllib.request.urlretrieve(url, file_path)
    return file_path


def parse_ndbc_stdmet_txt(path: Path) -> pd.DataFrame:
    """Parse one cached NDBC ``realtime2`` file into a raw column DataFrame (as strings or mixed)."""
    # Read space-delimited text, skipping the second row (units)
    df = pd.read_csv(
        path, 
        sep=r'\s+', 
        skiprows=[1], 
        na_values=['MM', '99.0', '99.00', '999', '9999'], 
        low_memory=False
    )
    
    # Clean up the header line which starts with a '#'
    df.rename(columns=lambda x: x.lstrip('#'), inplace=True)
    
    # Identify the year column (NDBC uses either YYYY or YY)
    yr_col = 'YYYY' if 'YYYY' in df.columns else 'YY'
    
    # Map NDBC columns to pandas datetime expected names
    date_mapping = {yr_col: 'year', 'MM': 'month', 'DD': 'day', 'hh': 'hour', 'mm': 'minute'}
    dt_df = df[list(date_mapping.keys())].rename(columns=date_mapping)
    
    # Create timezone-aware UTC timestamps
    df['timestamp_utc'] = pd.to_datetime(dt_df, errors='coerce', utc=True)
    
    # Extract swell columns and enforce numeric types
    swell_cols = ['WVHT', 'DPD', 'MWD', 'APD']
    for col in swell_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            df[col] = pd.NA
            
    return df[['timestamp_utc'] + swell_cols]


def fetch_buoy_swell(
    stations: tuple[str, ...] = NDBC_STATIONS,
    days: int = 30,
    use_cache: bool = False,
) -> pd.DataFrame:
    """
    End state for Week 1 buoy work: download (or use cache), parse, concatenate, filter by ``days``.

    ``use_cache``: if True and a cached file exists, skip re-downloading.
    """
    station_dfs = []
    cache_dir = Path(NDBC_CACHE_DIR) if NDBC_CACHE_DIR else Path("data/raw/ndbc")
    
    for station in stations:
        file_path = cache_dir / f"{station}.txt"
        
        if not (use_cache and file_path.exists()):
            file_path = download_station_txt(station, cache_dir)
            
        df = parse_ndbc_stdmet_txt(file_path)
        df['station'] = station
        station_dfs.append(df)
        
    if not station_dfs:
        return pd.DataFrame()
        
    combined_df = pd.concat(station_dfs, ignore_index=True)
    
    # Filter by timeframe
    cutoff_time = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    filtered_df = combined_df[combined_df['timestamp_utc'] >= cutoff_time].copy()
    
    # Rearrange columns to match output contract
    cols = ['timestamp_utc', 'station', 'WVHT', 'DPD', 'MWD', 'APD']
    return filtered_df[cols]


def main() -> None:
    try:
        df = fetch_buoy_swell(days=30, use_cache=False)
        print(df.head())
        print("rows:", len(df))
    except NotImplementedError:
        print("Implement this module — start at the docstring at the top of etl/fetch_buoy.py")


if __name__ == "__main__":
    main()
