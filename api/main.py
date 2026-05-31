import os
import io
import logging
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from google.cloud import storage

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI()

BUCKET = os.environ.get("GCS_BUCKET", "surfcast-sd-wind")
MODEL_BLOB = "models/surf_model.pkl"

FEATURE_COLS = [
    "WVHT", "DPD", "MWD", "APD", "tide_height_m",
    "wind_speed_mph", "wind_direction_deg", "is_calm",
    "sunrise_hour_utc", "sunset_hour_utc", "day_length_hours",
    "hours_since_sunrise", "season_sin", "season_cos",
    "temp_c", "humidity_pct",
]

LABEL_MAP = {
    "EPIC": "epic",
    "GOOD": "great",
    "FAIR_TO_GOOD": "good",
    "FAIR": "fair",
    "POOR_TO_FAIR": "poor_fair",
    "POOR": "poor",
    "VERY_POOR": "poor",
}

@lru_cache(maxsize=1)
def load_model():
    log.info("Loading model from GCS...")
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    blob = bucket.blob(MODEL_BLOB)
    buf = io.BytesIO()
    blob.download_to_file(buf)
    buf.seek(0)
    model = joblib.load(buf)
    log.info("Model loaded.")
    return model

class ForecastFeatures(BaseModel):
    WVHT: float
    DPD: float
    MWD: float
    APD: float
    tide_height_m: float
    wind_speed_mph: float
    wind_direction_deg: float
    is_calm: int
    sunrise_hour_utc: float
    sunset_hour_utc: float
    day_length_hours: float
    hours_since_sunrise: float
    season_sin: float
    season_cos: float
    temp_c: float
    humidity_pct: float

class PredictRequest(BaseModel):
    features: list[ForecastFeatures]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
def predict(req: PredictRequest):
    model = load_model()
    rows = [f.dict() for f in req.features]
    df = pd.DataFrame(rows)[FEATURE_COLS]
    preds = model.predict(df)
    mapped = [LABEL_MAP.get(p, "poor") for p in preds]
    return {"ratings": mapped}