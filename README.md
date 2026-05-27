# SurfCast SD

SurfCast SD is a student-built attempt to recreate the core idea of Surfline for a small set of San Diego surf breaks: collect ocean and weather data, turn it into surf-condition ratings, and display it in an interactive dashboard.

The first version will not be a perfect forecast product. The goal is to build a realistic end-to-end data project: ETL scripts, historical surf/weather data, feature engineering, machine learning experiments, cloud storage, scheduled refreshes, and a map-based app that makes the results easy to explore.

## Project Goal

Build a dashboard for San Diego surfers where a user can:

- View an interactive map of selected San Diego beaches.
- Click a beach to see current and recent surf conditions.
- Compare wind, buoy, swell, and tide patterns across breaks.
- See a simple surf quality rating produced from data-driven rules and, eventually, machine learning.
- Understand which environmental factors are driving each rating.

The project is inspired by Surfline, but scoped as a college student replication focused on learning data engineering, applied machine learning, and dashboard deployment.

## Current Surf Breaks

The current configuration in `etl/config.py` tracks:

- La Jolla Shores
- Blacks
- Pacific Beach Point

These are represented by approximate coordinates for weather lookup and Surfline spot IDs for label experiments.

## Data Sources

The project currently starts with these data sources:

| Source | Purpose | Current ETL |
| --- | --- | --- |
| NDBC buoy data | Swell height, period, direction, and related buoy observations | `etl/fetch_buoy.py` |
| National Weather Service API | Hourly wind speed and wind direction near each break | `etl/fetch_wind.py` |
| NOAA CO-OPS tides | Hourly tide height from La Jolla station `9410170` | `etl/fetch_tide.py` |
| Surfline ratings | Experimental labels / comparison target for surf quality | `etl/fetch_labels.py` |

Near-term ETL work is focused on expanding the scripts from short recent windows to roughly three years of historical data, so the model has enough examples to learn from.

## Technical Plan

### 1. Data Collection

ETL scripts fetch and normalize data into hourly time series. The main goal is to align each source onto a common hourly UTC timestamp so that buoy, wind, tide, and label data can be joined cleanly.

Core modules:

- `etl/fetch_buoy.py`: downloads and parses NDBC buoy observations for stations `46232` and `46254`.
- `etl/fetch_wind.py`: fetches NWS hourly wind forecasts for each configured beach coordinate.
- `etl/fetch_tide.py`: fetches NOAA tide heights and resamples them to hourly observations.
- `etl/fetch_labels.py`: fetches Surfline rating data for possible supervised learning labels.
- `etl/merge_hourly.py`: combines buoy, wind, and tide data into one hourly modeling table.
- `etl/score_surf.py`: contains an early rule-based surf quality scorer.

### 2. Feature Engineering

The modeling table will include surf-relevant features such as:

- Swell height
- Dominant swell period
- Mean wave direction
- Wind speed
- Wind direction
- Offshore/onshore wind indicators
- Tide height
- Time-of-day and seasonal features
- Rolling averages or lagged conditions

These features will support both simple rule-based scoring and future machine learning models.

### 3. Surf Condition Modeling

The first scoring version uses hand-written surf heuristics, such as better ratings for stronger swell periods, manageable wave heights, and offshore winds.

The longer-term plan is to train a machine learning model that predicts surf quality from historical conditions. Possible model targets include:

- Surfline-style rating categories
- A numeric quality score
- A custom `poor / fair / good / great` label generated from surf rules

Candidate models may include random forests, gradient boosted trees, or other tabular ML methods that work well on structured weather and ocean data.

### 4. Dashboard

The dashboard will be the main user-facing product. Planned features include:

- Interactive San Diego map with clickable surf break markers.
- Current condition panel for the selected beach.
- Charts for swell, wind, tide, and predicted surf rating.
- Historical trend views for model exploration.
- Beach-by-beach comparisons.

The project currently expects to use Plotly Dash for the app, with dashboard code living under `app/`.

### 5. Cloud Deployment

The planned production version will move away from intermediate local CSV files and use Google Cloud for storage and automation.

Target cloud architecture:

- Google Cloud Storage or BigQuery for storing raw and processed surf/weather data.
- Scheduled ETL jobs using Cloud Scheduler plus Cloud Run, Cloud Functions, or a similar service.
- Automated refreshes every few hours.
- A deployed dashboard that reads from the latest processed dataset.

This will make the project closer to a real data product instead of a notebook-only analysis.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `etl/` | Data ingestion, cleaning, merging, and scoring scripts |
| `app/` | Future Plotly Dash dashboard |
| `data/raw/` | Local raw data cache during development |
| `data/processed/` | Local processed datasets during development |
| `models/` | Future trained model artifacts and model notes |
| `notebooks/` | Exploratory analysis and modeling experiments |
| `docs/` | Project planning and technical notes |
| `scripts/` | Convenience scripts for running project workflows |
| `tests/` | Test suite |

## Local Setup

Create and activate a Python environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the current ETL modules from the repository root:

```bash
python -m etl.fetch_buoy
python -m etl.fetch_wind
python -m etl.fetch_tide
python -m etl.merge_hourly
```

Run tests:

```bash
python -m pytest tests/ -q
```

Before making heavy API requests, confirm the settings in `etl/config.py`, especially the NWS `User-Agent` and the configured stations/break coordinates.

## Development Roadmap

- Expand buoy, tide, and wind ingestion to cover approximately three years of historical data.
- Replace temporary local CSV workflows with durable cloud storage.
- Build a clean hourly feature table for model training.
- Create baseline rule-based surf ratings.
- Train and evaluate machine learning models for surf quality prediction.
- Build the interactive San Diego surf dashboard.
- Deploy the dashboard and schedule recurring data refreshes on Google Cloud.

## Project Status

This project is in early development. The repository currently contains the core ETL scaffolding and early implementations for buoy, wind, tide, hourly merging, and surf scoring. The next major milestone is turning those pieces into a reliable historical dataset that can support modeling and dashboard development.

## License

Add a license before public release or broader collaboration.
