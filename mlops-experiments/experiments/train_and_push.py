import mlflow
import mlflow.sklearn
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss
import prometheus_client
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import os
import shutil

# MLflow tracking server URL
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("iris_experiment")

# Prometheus PushGateway URL
PUSHGATEWAY = "http://pushgateway.monitoring.svc.cluster.local:9091"

X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

params_grid = [
    {"C": 0.1, "max_iter": 100},
    {"C": 1.0, "max_iter": 200},
    {"C": 10.0, "max_iter": 300},
]

best_acc = 0.0
best_run_id = None

for params in params_grid:
    with mlflow.start_run() as run:
        model = LogisticRegression(C=params["C"], max_iter=params["max_iter"])
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        loss = log_loss(y_test, model.predict_proba(X_test))

        mlflow.log_params(params)
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("loss", loss)
        mlflow.sklearn.log_model(model, "model")

        # Push metrics to PushGateway
        registry = CollectorRegistry()
        g_acc = Gauge("mlflow_accuracy", "Accuracy from MLflow run", ["run_id"], registry=registry)
        g_loss = Gauge("mlflow_loss", "Loss from MLflow run", ["run_id"], registry=registry)
        g_acc.labels(run.info.run_id).set(acc)
        g_loss.labels(run.info.run_id).set(loss)

        push_to_gateway(PUSHGATEWAY, job="mlflow_job", registry=registry)

        if acc > best_acc:
            best_acc = acc
            best_run_id = run.info.run_id
            best_model = model

# Save best model locally
if best_run_id:
    os.makedirs("best_model", exist_ok=True)
    mlflow.sklearn.save_model(best_model, "best_model")
    print(f"Best run: {best_run_id} with accuracy={best_acc}")
