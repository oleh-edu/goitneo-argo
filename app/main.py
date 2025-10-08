import os
import json
import time
import joblib
import logging
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import numpy as np
import requests

# Optional Great Expectations import
GE_AVAILABLE = False
try:
    from great_expectations.dataset import PandasDataset  # lightweight API
    import pandas as pd
    GE_AVAILABLE = True
except Exception:
    pass

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("aiops-inference")

REQS = Counter("inference_requests_total", "Total inference requests")
DRIFT = Counter("drift_events_total", "Total drift detection events")
LAT = Histogram("inference_latency_seconds", "Latency of predictions in seconds")

class SimpleDriftDetector:
    def __init__(self, baseline: np.ndarray):
        self.base_mean = baseline.mean(axis=0)
        self.base_std = baseline.std(axis=0) + 1e-8

    def score(self, x: np.ndarray) -> float:
        x_mean = x.mean(axis=0)
        z = np.abs((x_mean - self.base_mean) / self.base_std)
        return float(np.max(z))

    def detect(self, x: np.ndarray, z_threshold: float = 5.0) -> bool:
        return self.score(x) >= z_threshold

class PredictRequest(BaseModel):
    inputs: List[List[float]]

class PredictResponse(BaseModel):
    predictions: List[int]
    drift_detected: bool = False
    drift_score: float = 0.0

app = FastAPI(title="AIOps Quality Inference", version="0.2.0")

MODEL_PATH = os.environ.get("MODEL_PATH", "/models/model.pkl")
BASELINE_PATH = os.environ.get("BASELINE_PATH", "/models/baseline.npy")
DRIFT_WEBHOOK = os.environ.get("DRIFT_WEBHOOK", "")
REQUIRE_WEBHOOK = os.environ.get("REQUIRE_WEBHOOK", "false").lower() == "true"
EXPECTATIONS_PATH = os.environ.get("EXPECTATIONS_PATH", "/models/expectations.json")

model = None
detector = None
ge_suite = None

def _load_model():
    global model
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
    model = joblib.load(MODEL_PATH)
    log.info("Model loaded from %s", MODEL_PATH)

def _load_baseline():
    global detector
    if os.path.exists(BASELINE_PATH):
        baseline = np.load(BASELINE_PATH)
        detector = SimpleDriftDetector(baseline.astype(float))
        log.info("Baseline loaded from %s, shape=%s", BASELINE_PATH, baseline.shape)
    else:
        log.warning("Baseline not found at %s; stat drift disabled", BASELINE_PATH)

def _load_expectations():
    global ge_suite
    if GE_AVAILABLE and os.path.exists(EXPECTATIONS_PATH):
        with open(EXPECTATIONS_PATH, "r", encoding="utf-8") as f:
            ge_suite = json.load(f)
        log.info("Great Expectations suite loaded from %s", EXPECTATIONS_PATH)
    else:
        if not GE_AVAILABLE:
            log.info("Great Expectations not installed; GE drift disabled")
        else:
            log.info("EXPECTATIONS_PATH not found; GE drift disabled")

@app.on_event("startup")
def startup_event():
    _load_model()
    _load_baseline()
    _load_expectations()

@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None}

@app.get("/metrics")
def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

def _run_ge_validation(X: np.ndarray) -> bool:
    if not (GE_AVAILABLE and ge_suite):
        return False
    try:
        df = pd.DataFrame(X)
        ds = PandasDataset(df)
        ds._initialize_expectations()
        for e in ge_suite.get("expectations", []):
            getattr(ds, e["expectation_type"])(**e.get("kwargs", {}))
        result = ds.validate(result_format="SUMMARY")
        ok = bool(result.get("success", False))
        return not ok
    except Exception as e:
        log.warning("GE validation error: %s", e)
        return False

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    REQS.inc()
    start = time.time()

    X = np.array(req.inputs, dtype=float)
    if X.ndim != 2:
        raise HTTPException(status_code=400, detail="inputs must be 2D list")

    try:
        y = model.predict(X)
    except Exception as e:
        log.exception("Prediction error")
        raise HTTPException(status_code=500, detail=str(e))

    drift_detected = False
    drift_score = 0.0

    ge_drift = _run_ge_validation(X)
    if ge_drift:
        drift_detected = True

    if detector is not None:
        drift_score = detector.score(X)
        if detector.detect(X):
            drift_detected = True

    if drift_detected:
        DRIFT.inc()
        log.warning("Drift detected", extra={"score": drift_score, "sample": X[:1].tolist()})
        if DRIFT_WEBHOOK:
            try:
                resp = requests.post(DRIFT_WEBHOOK, json={"event": "drift_detected", "score": drift_score})
                log.info("Webhook status: %s", resp.status_code)
            except Exception as we:
                log.error("Webhook call failed: %s", we)
        elif REQUIRE_WEBHOOK:
            log.error("REQUIRE_WEBHOOK is true but DRIFT_WEBHOOK is not set")

    LAT.observe(time.time() - start)

    try:
        log.info(json.dumps({
            "event": "prediction",
            "inputs_sample": X[:1].tolist(),
            "predictions_sample": np.asarray(y)[:1].tolist(),
            "drift_detected": drift_detected,
            "drift_score": drift_score
        }))
    except Exception:
        pass

    return PredictResponse(predictions=[int(v) for v in y], drift_detected=drift_detected, drift_score=drift_score)
