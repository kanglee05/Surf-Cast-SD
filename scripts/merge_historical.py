#!/usr/bin/env python3
"""
Merge yearly historical CSVs into one combined file.

Run from repo root:
    python scripts/merge_historical.py
    python scripts/merge_historical.py --out data/processed/historical_combined.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", type=Path, default=Path("data/processed"),
                   help="Directory containing historical_YYYY.csv files")
    p.add_argument("--out", type=Path, default=Path("data/processed/historical_combined.csv"))
    args = p.parse_args()

    files = sorted(args.input_dir.glob("historical_20??.csv"))
    if not files:
        print(f"No historical_YYYY.csv files found in {args.input_dir}")
        return 1

    print(f"Found {len(files)} files: {[f.name for f in files]}")

    dfs = []
    for f in files:
        df = pd.read_csv(f, parse_dates=["timestamp_utc"])
        print(f"  {f.name}: {len(df)} rows")
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True).sort_values("timestamp_utc").reset_index(drop=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(args.out, index=False)

    print(f"\nCombined: {combined.shape[0]} rows × {combined.shape[1]} columns")
    print(f"Date range: {combined['timestamp_utc'].min()} → {combined['timestamp_utc'].max()}")
    print(f"Columns: {list(combined.columns)}")
    print(f"\nSaved → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
