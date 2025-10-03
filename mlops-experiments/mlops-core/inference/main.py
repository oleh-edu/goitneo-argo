import os
import sys
from fastapi import FastAPI
from pydantic import BaseModel
import mlflow.pyfunc
from dotenv import load_dotenv
import pandas as pd
from collections import deque
from datetime import datetime, timezone
import json
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from loguru import logger

# Great Expectations
try:
    from great_expectations.dataset import PandasDataset  # lightweight in-code usage
    GE_AVAILABLE = True
except Exception:
    GE_AVAILABLE = False

# configure json logging with loguru
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logger.remove()
logger.add(
    sink=sys.stdout if "sys" in globals() else sys.__stdout__,
    level=LOG_LEVEL,
    enqueue=True,
    backtrace=False,
    diagnose=False,
    serialize=True,  # JSON output
)

load_dotenv()

# mlflow config
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
MODEL_NAME = os.getenv("REGISTERED_MODEL_NAME", "iris_sgd_classification")
MODEL_STAGE = os.getenv("MODEL_STAGE", "Production")

MODEL_URI = f"models:/{MODEL_NAME}/{MODEL_STAGE}"

# load model
logger.info("Loading model", extra={"event": "model_load_start", "model_uri": MODEL_URI})
model = mlflow.pyfunc.load_model(MODEL_URI)
logger.info("Model loaded", extra={"event": "model_load_done", "model_uri": MODEL_URI})

# drift config
DRIFT_ENABLED = os.getenv("DRIFT_ENABLED", "true").lower() == "true"
DRIFT_WINDOW = int(os.getenv("DRIFT_WINDOW", "500"))
DRIFT_VALIDATE_EVERY = int(os.getenv("DRIFT_VALIDATE_EVERY", "100"))
EXPECTATIONS_PATH = os.getenv("EXPECTATIONS_PATH", "/app/expectations.json")
MIN_ROWS_TO_VALIDATE = int(os.getenv("DRIFT_MIN_ROWS", "50"))

app = FastAPI()

# health and readiness endpoints
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/readyz")
async def readyz():
    try:
        # minimal readiness check: model object exists
        return {"status": "ready" if model is not None else "not_ready"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}

# prometheus metrics
PREDICT_REQUESTS = Counter(
    "inference_predict_requests_total",
    "Total requests to /predict",
    labelnames=("status",),
)
PREDICT_LATENCY = Histogram(
    "inference_predict_latency_seconds",
    "Latency of /predict handler in seconds",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
DRIFT_STATUS = Gauge(
    "inference_drift_status",
    "Drift validation status (1=ok, 0=failed, -1=not-checked/disabled)",
)
DRIFT_FAILED_EXPECTATIONS = Gauge(
    "inference_drift_failed_expectations",
    "Number of failed expectations in last validation",
)

# app.mount("/metrics", make_asgi_app())

# start separate Prometheus metrics HTTP server on another port
METRICS_PORT = int(os.getenv("METRICS_PORT", "8001"))
try:
    start_http_server(METRICS_PORT)
    logger.info("Started Prometheus metrics HTTP server", extra={"event": "metrics_server_started", "port": METRICS_PORT})
except Exception as e:
    logger.error("Failed to start metrics server", extra={"event": "metrics_server_failed", "error": str(e)})

# Buffer of recent requests (list of lists -> rows)
_request_buffer = deque(maxlen=DRIFT_WINDOW)
_requests_since_validation = 0
_last_validation = {
    "enabled": DRIFT_ENABLED and GE_AVAILABLE,
    "success": None,
    "failed": [],
    "checked_at": None,
    "error": None,
}

def _set_drift_metrics_from_result(success: bool | None, failed_count: int):
    try:
        # Gauge semantics: 1 = drift detected (failure), 0 = healthy, -1 = not checked/disabled
        if success is None:
            DRIFT_STATUS.set(-1.0)
        else:
            DRIFT_STATUS.set(1.0 if (success is False) else 0.0)
        DRIFT_FAILED_EXPECTATIONS.set(float(failed_count))
    except Exception:
        pass

def _log_drift_event():
    # compact event for logs
    payload = {
        "event": "drift_validation",
        "enabled": _last_validation.get("enabled"),
        "success": _last_validation.get("success"),
        "failed_count": len(_last_validation.get("failed", [])),
        "checked_at": _last_validation.get("checked_at"),
        "error": _last_validation.get("error"),
    }
    # include first few failed expectations for context
    if _last_validation.get("failed"):
        payload["failed_examples"] = _last_validation["failed"][:3]

    if _last_validation.get("success") is False:
        # explicit drift message with loguru (JSON structured)
        logger.warning("Drift detected", extra={**payload, "event": "drift_detected"})
    else:
        logger.info("Drift validation run", extra=payload)

def _run_ge_validation(df: pd.DataFrame):
    global _last_validation
    if not (DRIFT_ENABLED and GE_AVAILABLE):
        _last_validation = {
            "enabled": False,
            "success": None,
            "failed": [],
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }
        _set_drift_metrics_from_result(None, 0)
        _log_drift_event()
        return

    try:
        if not os.path.exists(EXPECTATIONS_PATH):
            _last_validation = {
                "enabled": True,
                "success": None,
                "failed": [],
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "error": f"expectations file not found: {EXPECTATIONS_PATH}",
            }
            _set_drift_metrics_from_result(False, 0)
            _log_drift_event()
            return

        with open(EXPECTATIONS_PATH, "r") as f:
            suite_json = json.load(f)

        ds = PandasDataset(df)
        ds._initialize_expectations()
        for e in suite_json.get("expectations", []):
            e_type = e["expectation_type"]
            kwargs = e.get("kwargs", {})
            getattr(ds, e_type)(**kwargs)

        result = ds.validate(result_format="SUMMARY")
        failed = [
            {
                "type": r["expectation_config"]["expectation_type"],
                "kwargs": r["expectation_config"]["kwargs"],
            }
            for r in result.get("results", [])
            if not r.get("success", True)
        ]
        _last_validation = {
            "enabled": True,
            "success": bool(result.get("success", False)),
            "failed": failed,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }
        _set_drift_metrics_from_result(_last_validation["success"], len(failed))
        _log_drift_event()
    except Exception as e:
        _last_validation = {
            "enabled": True,
            "success": False,
            "failed": [],
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }
        _set_drift_metrics_from_result(False, 0)
        _log_drift_event()

class PredictRequest(BaseModel):
    instances: list[list[float]]

@app.post("/predict")
async def predict(payload: PredictRequest):
    global _requests_since_validation
    start = datetime.now().timestamp()
    status_label = "ok"
    try:
        df = pd.DataFrame(payload.instances)
        prediction = model.predict(df)

        # log prediction result
        try:
            preview = prediction.tolist()
            if len(preview) > 10:
                preview = preview[:10] + ["..."]
            logger.info(
                "Prediction served",
                extra={
                    "event": "predict",
                    "rows": len(payload.instances),
                    "predictions_preview": preview,
                },
            )
        except Exception:
            pass

        # drift buffer update (best effort; never block inference)
        try:
            if DRIFT_ENABLED and GE_AVAILABLE:
                for row in payload.instances:
                    _request_buffer.append(row)
                _requests_since_validation += len(payload.instances)

                if len(_request_buffer) >= max(MIN_ROWS_TO_VALIDATE, 1) and _requests_since_validation >= DRIFT_VALIDATE_EVERY:
                    buf_df = pd.DataFrame(list(_request_buffer), columns=df.columns if df.columns is not None else None)
                    _run_ge_validation(buf_df)
                    _requests_since_validation = 0
        except Exception:
            pass

        return {"predictions": prediction.tolist()}
    except Exception as ex:
        status_label = "error"
        logger.error("Prediction failed", extra={"event": "predict_error", "error": str(ex)})
        raise
    finally:
        try:
            PREDICT_REQUESTS.labels(status=status_label).inc()
            elapsed = datetime.now().timestamp() - start
            PREDICT_LATENCY.observe(elapsed)
        except Exception:
            pass
