#!/usr/bin/env python3
import os
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import mlflow.sklearn
from mlflow.artifacts import download_artifacts

from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import SGDClassifier

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# env
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
EXPERIMENT_NAME = os.getenv("EXPERIMENT_NAME", "Iris Classification")
REGISTERED_MODEL_NAME = os.getenv("REGISTERED_MODEL_NAME", "iris_sgd_classification")

LEARNING_RATES = [float(x) for x in os.getenv("LEARNING_RATES", "0.00001,0.001,0.01,0.1,1.0,10.0").split(",")]
EPOCHS = [int(x) for x in os.getenv("EPOCHS", "5,20,50").split(",")]

PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL", "http://localhost:9091")
JOB_NAME = os.getenv("JOB_NAME", "iris_training")

# mlflow setup
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
exp = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
experiment_id = exp.experiment_id if exp else mlflow.create_experiment(EXPERIMENT_NAME)

# data
X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42, stratify=y)

best = {"acc": -1.0, "run_id": None}

for lr in LEARNING_RATES:
    for ep in EPOCHS:
        with mlflow.start_run(experiment_id=experiment_id):
            mlflow.log_param("learning_rate", lr)
            mlflow.log_param("epochs", ep)

            model = Pipeline([
                ("scaler", StandardScaler()),
                ("clf", SGDClassifier(
                    loss="log_loss",
                    learning_rate="constant",
                    eta0=lr,
                    max_iter=ep,
                    tol=None,
                    random_state=42,
                )),
            ], memory=None)

            model.fit(X_train, y_train)
            y_proba = model.predict_proba(X_test)
            y_pred = y_proba.argmax(axis=1)

            acc = accuracy_score(y_test, y_pred)
            loss = log_loss(y_test, y_proba, labels=[0, 1, 2])

            mlflow.log_metric("accuracy", acc)
            mlflow.log_metric("loss", loss)
            mlflow.sklearn.log_model(model, "model", registered_model_name=REGISTERED_MODEL_NAME)

            # pushgateway
            run_id = mlflow.active_run().info.run_id
            try:
                reg = CollectorRegistry()
                g_acc = Gauge("accuracy", "Accuracy on test set", registry=reg)
                g_loss = Gauge("loss", "Log loss on test set", registry=reg)
                g_acc.set(acc)
                g_loss.set(loss)

                # group by run_id
                push_to_gateway(
                    PUSHGATEWAY_URL,
                    job=JOB_NAME,
                    registry=reg,
                    grouping_key={"run_id": run_id},
                )
            except Exception as e:
                print(f"[WARN] Pushgateway push failed for run {run_id}: {e}")

            if acc > best["acc"]:
                best.update({"acc": acc, "run_id": run_id})

print(f"Best run: {best['run_id']}  accuracy={best['acc']:.4f}")

# copy best model to ./best_model dir
if best["run_id"]:
    dst = Path("best_model")
    shutil.rmtree(dst, ignore_errors=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        local_dir = download_artifacts(run_id=best["run_id"], artifact_path="model", dst_path=tmpdir)
        shutil.copytree(local_dir, dst)
    print(f"Best model copied to: {dst.resolve()}")
else:
    print("No successful runs to select from.")
