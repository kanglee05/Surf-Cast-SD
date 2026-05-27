"""
Week 2 — Merge buoy + wind + tide on a common hourly clock

Inputs
------
- buoy  : from ``fetch_buoy.fetch_buoy_swell``   — columns: timestamp_utc, station, WVHT, DPD, MWD, APD
- wind  : from ``fetch_wind.fetch_wind_all_breaks`` — columns: timestamp_utc, break_id, wind_speed_mph, wind_direction_degrees
- tide  : from ``fetch_tide.fetch_tide_heights``  — columns: timestamp_utc, tide_height_m (optional)

Output
------
Wide DataFrame, one row per ``hour_utc``:
- Buoy columns  : ``buoy_{station}_{metric}``   e.g. ``buoy_46232_WVHT``
- Wind columns  : ``wind_{break}_{metric}``     e.g. ``wind_la_jolla_shores_speed_mph``
- Tide column   : ``tide_height_m``

``how`` controls join type:
  - "outer"  keeps every hour in any source (NaN where missing) — good for debugging
  - "inner"  keeps only hours present in all sources
"""

from __future__ import annotations

import pandas as pd


def merge_hourly(
    buoy: pd.DataFrame,
    wind: pd.DataFrame,
    tide: pd.DataFrame | None = None,
    how: str = "outer",
) -> pd.DataFrame:
    """Join buoy, wind, and optionally tide on aligned hourly timestamps.

    Output shape: one row per ``hour_utc``.
    """
    buoy = buoy.copy()
    wind = wind.copy()

    buoy["hour_utc"] = buoy["timestamp_utc"].dt.floor("h")
    wind["hour_utc"] = wind["timestamp_utc"].dt.floor("h")

    # --- buoy: pivot to wide ---
    swell_cols = [c for c in ["WVHT", "DPD", "MWD", "APD"] if c in buoy.columns]
    buoy_wide = buoy.pivot_table(
        index="hour_utc",
        columns="station",
        values=swell_cols,
        aggfunc="first",
    )
    # MultiIndex (metric, station) → buoy_{station}_{metric}
    buoy_wide.columns = [f"buoy_{station}_{metric}" for metric, station in buoy_wide.columns]
    buoy_wide = buoy_wide.reset_index()

    # --- wind: pivot to wide ---
    wind_cols = [c for c in ["wind_speed_mph", "wind_direction_degrees"] if c in wind.columns]
    wind_wide = wind.pivot_table(
        index="hour_utc",
        columns="break_id",
        values=wind_cols,
        aggfunc="first",
    )
    # MultiIndex (metric, break_id) → wind_{break_id}_{metric stripped of "wind_"}
    wind_wide.columns = [
        f"wind_{break_id}_{metric.replace('wind_', '')}"
        for metric, break_id in wind_wide.columns
    ]
    wind_wide = wind_wide.reset_index()

    merged = buoy_wide.merge(wind_wide, on="hour_utc", how=how)

    # --- tide: already one row per hour, just align and join ---
    if tide is not None and not tide.empty:
        tide = tide.copy()
        tide["hour_utc"] = tide["timestamp_utc"].dt.floor("h")
        tide_wide = tide[["hour_utc", "tide_height_m"]]
        merged = merged.merge(tide_wide, on="hour_utc", how=how)

    return merged


def main() -> None:
    from etl.fetch_buoy import fetch_buoy_swell
    from etl.fetch_tide import fetch_tide_heights
    from etl.fetch_wind import fetch_wind_all_breaks

    buoy = fetch_buoy_swell(days=30, use_cache=True)
    wind = fetch_wind_all_breaks()
    tide = fetch_tide_heights(days=30)
    merged = merge_hourly(buoy, wind, tide=tide)
    print(merged.head())
    print("shape:", merged.shape)
    print("columns:", list(merged.columns))


if __name__ == "__main__":
    main()
