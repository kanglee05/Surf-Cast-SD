"""Week 1 unit tests for merge_hourly — no network required."""

import pandas as pd

from etl.merge_hourly import merge_hourly


def _make_buoy() -> pd.DataFrame:
    return pd.DataFrame({
        "timestamp_utc": pd.to_datetime([
            "2026-04-24 01:20:00+00:00",
            "2026-04-24 01:50:00+00:00",
        ]),
        "station": ["46232", "46254"],
        "WVHT": [1.2, 1.5],
        "DPD": [12.0, 11.0],
        "MWD": [270.0, 265.0],
        "APD": [8.5, 8.0],
    })


def _make_wind() -> pd.DataFrame:
    return pd.DataFrame({
        "timestamp_utc": pd.to_datetime([
            "2026-04-24 01:00:00+00:00",
            "2026-04-24 01:00:00+00:00",
        ]),
        "break_id": ["la_jolla_shores", "pb_point"],
        "wind_speed_mph": [10.0, 8.0],
        "wind_direction_degrees": [270.0, 290.0],
    })


def test_output_columns_prefixed():
    merged = merge_hourly(_make_buoy(), _make_wind())
    assert "buoy_46232_WVHT" in merged.columns
    assert "buoy_46254_WVHT" in merged.columns
    assert "wind_la_jolla_shores_speed_mph" in merged.columns
    assert "wind_pb_point_direction_degrees" in merged.columns


def test_timestamps_floored_to_hour():
    merged = merge_hourly(_make_buoy(), _make_wind())
    assert "hour_utc" in merged.columns
    assert (merged["hour_utc"].dt.minute == 0).all()
    assert (merged["hour_utc"].dt.second == 0).all()


def test_inner_join_drops_non_overlapping():
    buoy = _make_buoy()
    wind = _make_wind().copy()
    wind["timestamp_utc"] = wind["timestamp_utc"] + pd.Timedelta(hours=5)
    merged = merge_hourly(buoy, wind, how="inner")
    assert len(merged) == 0


def test_outer_join_keeps_all_hours():
    buoy = _make_buoy()
    wind = _make_wind().copy()
    wind["timestamp_utc"] = wind["timestamp_utc"] + pd.Timedelta(hours=5)
    merged = merge_hourly(buoy, wind, how="outer")
    assert len(merged) == 2


def test_no_column_collisions():
    merged = merge_hourly(_make_buoy(), _make_wind())
    assert len(merged.columns) == len(set(merged.columns))
