"""
Surf condition scorer.

Takes a merged hourly DataFrame (output of merge_hourly) and returns a
rating column per break: "great", "good", or "bad".

Thresholds are tuned for San Diego beach breaks.
"""

from __future__ import annotations

import pandas as pd

# SD offshore wind comes from the east; onshore from the west.
# Degrees 45–135 = offshore quadrant (NE/E/SE).
_OFFSHORE_MIN = 45
_OFFSHORE_MAX = 135


def _wind_is_offshore(degrees: float) -> bool:
    return _OFFSHORE_MIN <= degrees <= _OFFSHORE_MAX


def _rate_hour(
    wvht: float,   # wave height in meters
    dpd: float,    # dominant period in seconds
    wind_speed: float,       # mph
    wind_dir: float,         # degrees
) -> str:
    """Return 'great', 'good', or 'bad' for one hour of conditions."""
    import math

    if any(math.isnan(v) for v in [wvht, dpd, wind_speed, wind_dir]):
        return "bad"

    offshore = _wind_is_offshore(wind_dir)
    wvht_ft = wvht * 3.281  # convert meters → feet

    # --- Great ---
    if (
        5 <= wvht_ft <= 10
        and dpd >= 14
        and wind_speed <= 10
        and offshore
    ):
        return "great"

    # --- Good ---
    if (
        3 <= wvht_ft <= 10
        and dpd >= 10
        and wind_speed <= 15
    ):
        return "good"

    # --- Bad ---
    return "bad"


def score_surf(merged: pd.DataFrame, station: str = "46232", break_id: str = "la_jolla_shores") -> pd.DataFrame:
    """Add a 'surf_rating' column to a merged hourly DataFrame.

    Parameters
    ----------
    merged:   output of merge_hourly()
    station:  NDBC station to pull swell from (default: 46232 Point Loma South)
    break_id: NWS break to pull wind from (default: la_jolla_shores)

    Returns
    -------
    Copy of merged with an added 'surf_rating' column: 'great' | 'good' | 'bad'
    """
    df = merged.copy()

    wvht_col = f"buoy_{station}_WVHT"
    dpd_col = f"buoy_{station}_DPD"
    wspd_col = f"wind_{break_id}_speed_mph"
    wdir_col = f"wind_{break_id}_direction_degrees"

    missing = [c for c in [wvht_col, dpd_col, wspd_col, wdir_col] if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns in merged DataFrame: {missing}")

    df["surf_rating"] = [
        _rate_hour(row[wvht_col], row[dpd_col], row[wspd_col], row[wdir_col])
        for _, row in df.iterrows()
    ]

    return df


def summarize_ratings(scored: pd.DataFrame) -> pd.DataFrame:
    """Return a count + percentage breakdown of ratings."""
    counts = scored["surf_rating"].value_counts().rename("count")
    pct = (counts / len(scored) * 100).round(1).rename("pct")
    return pd.concat([counts, pct], axis=1)
