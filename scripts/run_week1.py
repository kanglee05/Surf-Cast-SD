#!/usr/bin/env python3
"""
Week 1 — Single entry script (wire this up last)

Once ``fetch_buoy``, ``fetch_wind``, and ``merge_hourly`` are implemented, this script should:

1. Load buoy swell for the last ``--days`` days.
2. Load wind for all breaks.
3. Merge to one hourly DataFrame.
4. Optionally write CSV (or Parquet if you add ``pyarrow``).

Run from repository root::

    python scripts/run_week1.py --days 30
    python scripts/run_week1.py --days 30 --out data/processed/week1_merged.csv

The ``sys.path`` hack below lets you run without installing a package; alternatively use
``pip install -e .`` if the club adds a ``pyproject.toml`` later.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etl.config import NOAA_TIDES_CACHE_DIR, NWS_CACHE_DIR  # noqa: E402
from etl.fetch_buoy import fetch_buoy_swell  # noqa: E402
from etl.fetch_tide import fetch_tide_heights  # noqa: E402
from etl.fetch_wind import fetch_wind_all_breaks  # noqa: E402
from etl.merge_hourly import merge_hourly  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="SurfCast SD Week 1 — buoy + wind merge")
    p.add_argument("--days", type=int, default=30, help="Days of buoy history to keep")
    p.add_argument(
        "--buoy-cache",
        action="store_true",
        help="Use cached NDBC files under data/raw/ndbc if present",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional path to write CSV (or .parquet if you implement + install pyarrow)",
    )
    args = p.parse_args()

    try:
        print("Fetching buoy swell…")
        buoy = fetch_buoy_swell(days=args.days, use_cache=args.buoy_cache)
        print(f"  buoy rows: {len(buoy)}")

        print("Fetching NWS wind…")
        NWS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        wind = fetch_wind_all_breaks(cache_dir=NWS_CACHE_DIR)
        print(f"  wind rows: {len(wind)}")

        print("Fetching NOAA tides…")
        NOAA_TIDES_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tide = fetch_tide_heights(days=args.days, cache_dir=NOAA_TIDES_CACHE_DIR)
        print(f"  tide rows: {len(tide)}")

        merged = merge_hourly(buoy, wind, tide=tide, how="outer")
        print(f"Merged shape: {merged.shape}")
        print(merged.head(3))

        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            if args.out.suffix.lower() == ".parquet":
                merged.to_parquet(args.out, index=False)
            else:
                merged.to_csv(args.out, index=False)
            print(f"Wrote {args.out}")
    except NotImplementedError as e:
        print(
            "\nNot implemented yet — finish the Week 1 modules in `etl/` first.\n"
            f"Details: {e}\n",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
