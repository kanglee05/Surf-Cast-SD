# Week 1 — Surfline / surfpy scoping

**Owner:** Yra Climaco  
**Due:** end of Week 1  

## 1. Library / access
surfpy (mpiannucci/surfpy) is a Python surfing math library primarily 
for NOAA buoy data and wave model forecasts. Installable via:
pip install git+https://github.com/mpiannucci/surfpy

Last commit: 2023. Version 0.98.0.

**Key finding:** surfpy has zero Surfline integration. It exposes 
BuoyStation, TideStation, WaveModel, and WeatherApi — no Surfline 
ratings anywhere in the library. Cannot be used for labels.

pysurfline (wolfinger/pysurfline) — available on PyPI, version 0.0.3.
Returns wave, wind, tides, weather data but has no ratings endpoint.
Cannot be used for training labels.

**Solution:** Hit the Surfline internal rating API directly using 
requests — no library needed.

## 2. What can you actually retrieve?
Tested two Surfline endpoints:

**Conditions endpoint (free, but ratings null):**
https://services.surfline.com/kbyg/spots/forecasts/conditions?spotId=XXXX&days=1
- Returns headline text, observation text
- am.rating and pm.rating are null without Premium+ account

**Rating endpoint (free, numeric ratings available):**
https://services.surfline.com/kbyg/spots/forecasts/rating?spotId=XXXX&days=5
- Returns hourly ratings with key (POOR, FAIR, GOOD etc.) and numeric value (0-5)
- No authentication required
- Implemented in etl/fetch_labels.py

Sample fields returned:
- timestamp (Unix epoch)
- rating.key → string e.g. "POOR_TO_FAIR"
- rating.value → float e.g. 2.166

Spot IDs for our three breaks (found in Surfline URLs):
- La Jolla Shores: 5842041f4e65fad6a77088cc
- Blacks: 5842041f4e65fad6a770883b
- PB Point: 5842041f4e65fad6a77088c2

## 3. Label mapping
Surfline rating keys map to numeric values natively:

- VERY_POOR → ~0.3
- POOR → 1.0
- POOR_TO_FAIR → 2.0
- FAIR → 3.0
- FAIR_TO_GOOD → 4.0
- GOOD → 4.0-5.0
- EPIC → 5.0

The API returns the numeric value directly so no manual 
mapping is needed. We use rating_value as the label column.

## 4. Historical depth
The rating endpoint returns forecast data only — up to 5 days 
ahead. It does not provide historical ratings.

To build a training dataset we need to run fetch_labels.py 
daily and accumulate ratings over time. Starting now gives 
us data going forward but not backwards.

This is the key limitation — we have no historical labels yet.

## 5. Risk
- surfpy: no Surfline support, useless for labels
- pysurfline: available but no ratings endpoint, unusable for labels
- Direct API: unofficial endpoint, no authentication required
  but Surfline could add auth or change URL anytime
- Mitigation: all responses cached to data/raw/surfline/,
  never re-fetch what is already saved locally
- Legal gray area: data is publicly visible on surfline.com
  without login. Mentor should confirm this is acceptable.

## 6. Recommendation

**Feasible for Week 2 going forward — not for historical data.**

fetch_labels.py is implemented and working. It returns a clean 
DataFrame with timestamp_utc, break_id, rating_key, rating_value 
for all three breaks up to 5 days ahead.

For training the model the team needs to decide:
1. Run fetch_labels.py daily starting now and train on 
   accumulated data (takes weeks to build enough history)
2. Find a way to get historical labels — mentor to advise
3. Build a rules-based scoring formula as a short-term 
   substitute while accumulating real labels

Need from mentor: confirm legal/ToS acceptability of using 
Surfline's internal rating API, and decide on historical 
label strategy.

## Notes

_Team notes / findings_
