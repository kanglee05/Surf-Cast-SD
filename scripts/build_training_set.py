#!/usr/bin/env python3
"""
Merge historical_combined.csv (features) with surfline_labels.csv (labels)
into one training-ready CSV.

Run from repo root:
    python scripts/build_training_set.py

Output: data/processed/training_set.csv
Columns: all feature columns + break_id + rating_key + rating_value
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROCESSED = Path("data/processed")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--features", type=Path,
                   default=PROCESSED / "historical_combined.csv")
    p.add_argument("--labels",   type=Path,
                   default=PROCESSED / "surfline_labels.csv")
    p.add_argument("--out",      type=Path,
                   default=PROCESSED / "training_set.csv")
    args = p.parse_args()

    print(f"Loading features: {args.features}")
    features = pd.read_csv(args.features, parse_dates=["timestamp_utc"])
    print(f"  {features.shape[0]} rows, {features.shape[1]} columns")

    print(f"\nLoading labels: {args.labels}")
    labels = pd.read_csv(args.labels, parse_dates=["timestamp_utc"])
    print(f"  {labels.shape[0]} rows")
    print(f"  Rating breakdown:\n{labels['rating_key'].value_counts().to_string()}")

    # Floor both to the hour so timestamps align cleanly
    features["hour_utc"] = features["timestamp_utc"].dt.floor("h")
    labels["hour_utc"]   = labels["timestamp_utc"].dt.floor("h")

    # Labels have a break_id column; features have a station column.
    # We merge on hour only — each hour gets the same label for all stations
    # (buoy data is station-specific but the surf rating is per break, not per buoy).
    # Result: one row per (hour, station, break_id) combination.
    merged = features.merge(
        labels[["hour_utc", "break_id", "rating_key", "rating_value"]],
        on="hour_utc",
        how="inner",
    )

    merged = merged.drop(columns="hour_utc")
    merged = merged.sort_values(["timestamp_utc", "break_id", "station"]).reset_index(drop=True)

    print(f"\nMerged training set: {merged.shape[0]} rows × {merged.shape[1]} columns")
    print(f"Date range: {merged['timestamp_utc'].min()} → {merged['timestamp_utc'].max()}")
    print(f"Breaks: {merged['break_id'].unique().tolist()}")
    print(f"Stations: {merged['station'].unique().tolist()}")
    print(f"\nSample:")
    print(merged.head(6).to_string())

    args.out.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.out, index=False)
    print(f"\nSaved → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
