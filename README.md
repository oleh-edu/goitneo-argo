# 🧠 AIOps Quality Project

AIOps Quality is a **production-ready example of an MLOps-quality assurance pipeline**, featuring:

- A **FastAPI inference service** with drift detection (Great Expectations + statistical)
- A **Helm chart** for deployment in Kubernetes
- **ArgoCD GitOps integration** for automated sync and self-heal
- **Prometheus + Grafana** for metrics and observability
- **Loki/Promtail** for logging of input data and predictions
- A **training pipeline** (`model/train.py`) for model retraining
- Infrastructure managed and automated via **GitHub Actions**

---

## 📂 Project Structure

```bash
aiops-quality-project/
├── app/
│   └── main.py                     # FastAPI inference service with drift detection
├── model/
│   └── train.py                    # Model training and artifact generation
├── helm/
│   ├── Chart.yaml                  # Helm chart metadata
│   ├── values.yaml                 # Configurable values (image, ports, env)
│   └── templates/
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── configmap.yaml
│       └── _helpers.tpl
├── argocd/
│   └── application.yaml            # ArgoCD Application manifest
├── grafana/
│   └── dashboards.json             # Grafana dashboard for inference metrics
├── prometheus/
│   └── additionalScrapeConfigs.yaml # Prometheus scrape configuration
├── Dockerfile                      # Container definition
└── README.md                       # Documentation
```

---

## 🚀 Overview

The project demonstrates a **complete MLOps feedback loop**:

1. **Model training** using `train.py` — generates `model.pkl`, `baseline.npy`, and a `Great Expectations` ruleset.
2. **FastAPI inference service** loads these artifacts and:
   - Handles `/predict` requests
   - Calculates predictions
   - Monitors for data drift
   - Logs predictions and drift detection events
   - Exposes Prometheus metrics
3. **Helm & ArgoCD** ensure GitOps-based deployment and self-healing in Kubernetes.
4. **Prometheus + Grafana** visualize requests, latency, and drift events.
5. **GitHub Actions** can trigger retraining, reset, or destroy infrastructure.

---

## ⚙️ Inference Service (FastAPI)

Located in `app/main.py`.

### Features

- **/predict** — accepts JSON input, returns predictions
- **/metrics** — exposes Prometheus-compatible metrics
- **/health** — readiness endpoint

### Prometheus Metrics

| Metric Name | Description |
|--------------|-------------|
| `inference_requests_total` | Total number of prediction requests |
| `inference_latency_seconds` | Histogram of model latency |
| `drift_events_total` | Number of detected drift events |

---

## 🧮 Drift Detection

The service supports **two types of drift detection**:

### 1. Statistical Drift (built-in)

- Calculates z-score difference from the baseline mean.
- Triggered when `z > 5.0`.

### 2. Great Expectations (optional)

- Loads `expectations.json` rules.
- Fails validation if input distribution violates expectations.

When drift is detected:

- It’s logged (`Drift detected`).
- `drift_events_total` metric increments.
- Optional **webhook** is triggered via `DRIFT_WEBHOOK` environment variable.

---

## 🧰 Model Training (`model/train.py`)

A simple example using the **Iris dataset**.

```bash
python model/train.py
```

This generates:

- `model_artifacts/model.pkl`
- `model_artifacts/baseline.npy`
- `model_artifacts/expectations.json`

Artifacts can be mounted in the container under `/models`.

---

## 🐳 Docker Build

The `Dockerfile` builds a lightweight inference image.

```bash
docker build -t aiops-quality:latest .
docker run -p 8000:8000 aiops-quality:latest
```

Then test locally:

```bash
curl -X POST http://localhost:8000/predict   -H "Content-Type: application/json"   -d '{"inputs": [[5.1,3.5,1.4,0.2],[6.5,3.0,5.5,1.8]]}'
```

Expected output:

```json
{
  "predictions": [0, 2],
  "drift_detected": false,
  "drift_score": 1.23
}
```

---

## ☸️ Helm Deployment

Helm chart is located in `helm/`.

### Example Install:

```bash
helm install aiops-quality ./helm   --set image.repository=ghcr.io/your-org/aiops-quality   --set image.tag=latest
```

The deployment:

- Mounts model artifacts as ConfigMap
- Annotates pods for Prometheus scraping
- Exposes the service on port `8000`

---

## 🔁 ArgoCD Integration

`argocd/application.yaml` defines the GitOps deployment:

```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
  syncOptions:
    - CreateNamespace=true
```

After adding this application:

```bash
kubectl apply -f argocd/application.yaml
```

ArgoCD will continuously sync from your repository and auto-heal if the deployment drifts.

---

## 📊 Monitoring & Logging

### Prometheus

- Scrapes metrics via annotations:

  ```yaml
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
  ```

### Grafana

Dashboard (`grafana/dashboards.json`) includes:

- Requests per second
- Latency (p50/p90)
- Drift events count

### Loki + Promtail

All logs are emitted via `stdout` and automatically collected by Promtail.

Example log line:

```bash
INFO {"event": "prediction", "inputs_sample": [[5.1,3.5,1.4,0.2]], "predictions_sample": [0], "drift_detected": false, "drift_score": 1.23}
```

---

## 🧩 Prometheus Scrape Config (Optional)

Example addition to Prometheus configuration:

```yaml
additionalScrapeConfigs:
  - job_name: 'aiops-quality'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: "true"
```

---

## ⚡ GitHub Actions (CI/CD)

Workflows are defined under `.github/workflows/`:

- `reset.yml` – Reset infrastructure (destroy + apply)
- `destroy.yml` – Destroy all Terraform-managed resources
- `train-model.yml` – Trigger AWS Step Function to retrain model

Example trigger:

```bash
gh workflow run "Train Model"
```

Each workflow authenticates via **OIDC** and manages secrets automatically.

---

## ✅ Verification Checklist

| Task | Verification Command |
|------|----------------------|
| API is running | `kubectl port-forward svc/aiops-quality 8000:80` |
| Health check | `curl localhost:8000/health` |
| Prediction | `curl -X POST localhost:8000/predict ...` |
| Logs include drift | `kubectl logs -l app=aiops-quality` |
| Prometheus scrape | Check `/metrics` |
| Grafana metrics visible | Dashboard “AIOps Quality - Inference Overview” |
| Retraining triggered | `gh workflow run train-model.yml` |
| ArgoCD syncs deployment | `argocd app sync aiops-quality` |

---

## 🔄 Retraining Workflow

When drift is detected, or new data is available:

1. Run GitHub Action `Train Model`.
2. AWS Step Function starts model retraining.
3. New artifacts are built and pushed to the container registry.
4. ArgoCD detects Helm chart change → redeploys updated service.

---

## 🧩 Environment Variables

| Variable | Description | Default |
|-----------|-------------|----------|
| `MODEL_PATH` | Path to trained model | `/models/model.pkl` |
| `BASELINE_PATH` | Path to baseline dataset | `/models/baseline.npy` |
| `EXPECTATIONS_PATH` | Path to Great Expectations suite | `/models/expectations.json` |
| `DRIFT_WEBHOOK` | Optional webhook for drift alerts | `""` |
| `REQUIRE_WEBHOOK` | Enforce webhook presence | `"false"` |

---

## 🧭 Summary

This repository provides a **complete example of an AI/ML inference pipeline with drift monitoring, observability, and GitOps automation**, designed for reproducibility and production readiness.

**Key Benefits:**

- End-to-end reproducible workflow
- Drift-aware inference with explainability
- GitOps + CI/CD automation
- Observability-first design
- Easily extendable for new models or datasets
