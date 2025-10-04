# MLOps Experiments – Iris SGD Classification Demo

This repository demonstrates a **production-like MLOps workflow** for the Iris classification problem.  
It covers **model training & promotion with MLflow**, **containerized inference service with FastAPI**, **CI/CD with ArgoCD**, and **observability with Prometheus/Grafana**.

---

## 📂 Project Structure

```bash
.
├── argocd/                     # ArgoCD manifests
│   ├── applications/           # MLflow, MinIO, Postgres, PushGateway, Inference
│   │   ├── inference.yaml
│   │   ├── minio.yaml
│   │   ├── mlflow.yaml
│   │   ├── postgres.yaml
│   │   └── pushgateway.yaml
│   └── namespaces/             # Namespace definitions
│       ├── mlflow-namespace.yaml
│       └── monitoring-namespace.yaml
├── best_model/                 # Best model exported by training
│   ├── MLmodel
│   ├── model.pkl
│   ├── requirements.txt
│   ├── conda.yaml
│   ├── python_env.yaml
│   ├── input_example.json
│   └── serving_input_example.json
├── mlops-core/
│   ├── charts/inference/       # Helm chart for inference service
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       ├── deployment.yaml
│   │       ├── ingress.yaml
│   │       ├── service.yaml
│   │       └── _helpers.tpl
│   ├── inference/              # Inference service (FastAPI + Uvicorn)
│   │   ├── main.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── expectations.json
│   ├── model/                  # Training & promotion scripts
│   │   ├── train_and_push.py
│   │   ├── promote.py
│   │   ├── requirements.txt
│   │   └── best_model/         # Copy of best model after training
│   │       ├── MLmodel
│   │       ├── model.pkl
│   │       ├── requirements.txt
│   │       ├── conda.yaml
│   │       └── python_env.yaml
│   └── simulate_drift.sh       # Drift simulation script
└── README.md
```

---

## 🚀 Prerequisites

- **Minikube** (or Kubernetes cluster)
- **kubectl**
- **ArgoCD** (deployed in `infra-tools`)
- **Docker** (to build inference image)
- **Python 3.10+** for training scripts

---

## 🏗️ Deploy Infrastructure on Minikube

### 1. Start Minikube

```bash
minikube start --cpus=4 --memory=8192 --driver=docker
```

(Optional) Enable registry:

```bash
minikube addons enable registry
```

### 2. Apply Namespaces

```bash
kubectl apply -f argocd/namespaces/
```

### 3. Deploy Applications

```bash
kubectl apply -f argocd/applications/
```

Check:

```bash
argocd app list
```

---

## 🔑 ArgoCD UI

Forward ArgoCD:

```bash
kubectl port-forward svc/argocd-server -n infra-tools 8080:443
argocd login localhost:8080 --insecure --username admin --password <your-password>
```

---

## 📊 Services

### MLflow

```bash
kubectl -n mlflow port-forward svc/mlflow-mlflow 5000:5000
```

Access: [http://localhost:5000](http://localhost:5000)

### PushGateway

```bash
kubectl -n monitoring port-forward svc/pushgateway-prometheus-pushgateway 9091:9091
```

Access: [http://localhost:9091](http://localhost:9091)

---

## 🧪 Training & Promotion

### Setup environment

```bash
cd mlops-core/model
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Train & log to MLflow

```bash
python train_and_push.py
```

This will:

- Train SGDClassifier on Iris
- Log to MLflow
- Push metrics to PushGateway
- Copy best model to `best_model/`

### Promote best model

```bash
python promote.py
```

Promotion rules:

- Accuracy ≥ `PROMOTE_MIN_ACCURACY` (default 0.9)
- Archives old version in Production
- Sets alias `Production`

---

## 🐳 Build Inference Service

```bash
cd mlops-core/inference
docker build -t localhost:5000/inference:0.1.2 .
docker push localhost:5000/inference:0.1.2
```

ArgoCD app `inference.yaml` uses this image.

---

## ⚡ Inference API

Namespace: `inference`  
Service: FastAPI + Uvicorn on `:8080`

Endpoints:

- `GET /healthz`
- `GET /readyz`
- `POST /predict`
- `GET /metrics` (on port `8001`)

### Test

```bash
kubectl -n inference port-forward svc/inference 8080:8080
```

Health:

```bash
curl http://localhost:8080/healthz
```

Predict (list):

```bash
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{"instances": [[5.1, 3.5, 1.4, 0.2], [6.2, 3.4, 5.4, 2.3]]}'
```

Predict (dict):

```bash
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [
      {"sepal length (cm)": 5.1, "sepal width (cm)": 3.5, "petal length (cm)": 1.4, "petal width (cm)": 0.2},
      {"sepal length (cm)": 6.2, "sepal width (cm)": 3.4, "petal length (cm)": 5.4, "petal width (cm)": 2.3}
    ]
  }'
```

---

## 📉 Drift Simulation

```bash
kubectl -n inference port-forward svc/inference 8080:8080
cd mlops-core
chmod +x simulate_drift.sh
./simulate_drift.sh
```

This will send baseline + drifted requests.

---

## 📈 Monitoring in Grafana

```bash
kubectl -n monitoring port-forward svc/grafana 8081:80
```

Access: [http://localhost:8081](http://localhost:8081)  
Login: `admin/mlops` → Dashboard → *Inference Service Overview*

---

## ✅ Summary

- Full MLOps workflow: **MLflow + MinIO + Postgres + ArgoCD + FastAPI + Prometheus**
- Train/promote pipeline with metrics-based promotion
- Containerized inference with drift detection
- Ready to run in Minikube or production Kubernetes

## 🔄 Typical Workflow (Step-by-Step)

1. **Start Minikube cluster**  

   ```bash
   minikube start --cpus=4 --memory=8192 --driver=docker
   ```

2. **Apply namespaces**  

   ```bash
   kubectl apply -f argocd/namespaces/
   ```

3. **Deploy applications via ArgoCD**  

   ```bash
   kubectl apply -f argocd/applications/
   ```

4. **Access ArgoCD UI**  

   ```bash
   kubectl port-forward svc/argocd-server -n infra-tools 8080:443
   argocd login localhost:8080 --insecure --username admin --password <your-password>
   ```

5. **Port-forward key services**  

   ```bash
   # MLflow
   kubectl -n mlflow port-forward svc/mlflow-mlflow 5000:5000

   # MinIO
   kubectl -n mlflow port-forward svc/minio 9000:9000

   # Postgres
   kubectl -n mlflow port-forward svc/postgres-postgresql 5432:5432

   # PushGateway
   kubectl -n monitoring port-forward svc/pushgateway-prometheus-pushgateway 9091:9091

   # Grafana
   kubectl -n monitoring port-forward svc/grafana 8081:80

   # Inference API
   kubectl -n inference port-forward svc/inference 8080:8080
   ```

6. **Run training & select best model**  

   ```bash
   cd mlops-core/model
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

   python train_and_push.py
   python promote.py
   ```

7. **Build & push inference image**  

   ```bash
   cd mlops-core/inference
   docker build -t localhost:5000/inference:0.1.2 .
   docker push localhost:5000/inference:0.1.2
   ```

8. **Test inference service**  

   ```bash
   curl http://localhost:8080/healthz
   curl -X POST http://localhost:8080/predict \
     -H "Content-Type: application/json" \
     -d '{"instances": [[5.1, 3.5, 1.4, 0.2]]}'
   ```

9. **Simulate drift**  

   ```bash
   cd mlops-core
   ./simulate_drift.sh
   ```

10. **Monitor in Grafana**  
    Open: [http://localhost:8081](http://localhost:8081) → Dashboard → *Inference Service Overview*
