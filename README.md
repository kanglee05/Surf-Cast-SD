# SurfCast SD

**Repository:** [github.com/Igosain08/surfcastSD](https://github.com/Igosain08/surfcastSD)

College club project: **San Diego surf conditions → data pipeline → ML + app** (see your project overview doc). This repository is a **Week 1 starter layout**: **instructions and stubs**, not finished code — the team implements the ETL and merge.

## For club members — workflow

1. **Clone** this repo: `git clone https://github.com/Igosain08/surfcastSD.git`
2. **Create a branch** for your task (e.g. `week1/buoy-etl`).
3. **Implement** the file(s) assigned to you (see Week 1 goals below).
4. **Open a PR**; mentor / club leads review.

Python environment:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Edit ``etl/config.py`` (especially **NWS User-Agent** — required by api.weather.gov).

Run the Week 1 script (stubs exit with a clear message until you implement):

```bash
python scripts/run_week1.py --days 30
```

Individual modules:

```bash
python -m etl.fetch_buoy
python -m etl.fetch_wind
python -m etl.merge_hourly
```

Tests (placeholder passes until you add real ones):

```bash
python -m pytest tests/ -q
```

## Week 1 goal (club deliverable)

By the end of Week 1: **one command** (``scripts/run_week1.py``) produces a **clean hourly DataFrame** combining:

- **Buoy swell** — NDBC stations `46232` and `46254`; columns such as `WVHT`, `DPD`, `MWD`, `APD` (names may match NDBC / your parser).
- **Wind** — from **api.weather.gov** for the three breaks (coordinates in ``etl/config.py``), hourly rows aligned for merge.

**Surfline / surfpy:** research only this week — fill in ``docs/WEEK1_SURFLINE_SCOPING.md`` (no production scrape unless mentor approves).

**UI note:** one short paragraph in ``docs/DASH_VS_STREAMLIT.md`` for the Week 5 app choice.

## Repo layout

| Path | Purpose |
|------|---------|
| `etl/config.py` | Paths, station IDs, break lat/lon, `User-Agent` — **edit** |
| `etl/fetch_buoy.py` | **You implement** — NDBC download + parse + cache |
| `etl/fetch_wind.py` | **You implement** — NWS hourly wind per break |
| `etl/merge_hourly.py` | **You implement** — join on hourly UTC timestamp |
| `scripts/run_week1.py` | Wire-up script — works once the three modules above do |
| `docs/WEEK1_SURFLINE_SCOPING.md` | Research writeup template |
| `docs/DASH_VS_STREAMLIT.md` | Short UI recommendation template |
| `data/raw/`, `data/processed/` | Local data — see READMEs inside (generally not committed) |

## For the mentor

Set **branch protection** / PR rules on GitHub if you want, and assign Week 1 owners to each `etl/` file + docs tasks. The stubs intentionally **`raise NotImplementedError`** until the team implements them.

## License

Add a license file when the club is ready (e.g. MIT for student work).
