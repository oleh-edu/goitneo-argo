# MLOps Experiments

This project demonstrates how to deploy an infrastructure for **MLflow**, **PostgreSQL/MySQL**, **MinIO**, 
and **Prometheus PushGateway** using **Argo CD** in Kubernetes.  
It also includes a sample training script that logs parameters and metrics to MLflow and pushes metrics to PushGateway.

---

## 📂 Project Structure

```bash
mlops-experiments/
├── argocd/
│   ├── namespaces/
│   │   ├── mlflow-namespace.yaml         # Namespace for MLflow
│   │   └── monitoring-namespace.yaml     # Namespace for PushGateway
│   ├── applications/
│   │   ├── mlflow.yaml                   # MLflow Tracking Server
│   │   ├── minio.yaml                    # MinIO (artifacts)
│   │   ├── postgres.yaml                 # PostgreSQL/MySQL database
│   │   └── pushgateway.yaml              # Prometheus PushGateway
│   └── configmap/
│       └── argocd-cm.yaml                # ArgoCD config with OCI enabled
├── experiments/
│   ├── train_and_push.py                 # Training + Push script
│   └── requirements.txt                  # Python dependencies
├── best_model/                           # Best model saved locally
└── README.md
```

---

## 🚀 Deployment

### 1. Create Namespaces

```bash
kubectl apply -f argocd/namespaces/mlflow-namespace.yaml
kubectl apply -f argocd/namespaces/monitoring-namespace.yaml
```

### 2. Deploy Applications via Argo CD

Apply all Application manifests:

```bash
kubectl apply -f argocd/applications/
```

Check application status in Argo CD UI or CLI:

```bash
argocd app list
```

### 3. Access Argo CD UI

Forward the ArgoCD server service:

```bash
kubectl port-forward svc/argocd-server -n infra-tools 8080:443
```

Login with admin user:

```bash
argocd login localhost:8080 --insecure --username admin --password <your-password>
```

### 4. Access Services

- **MLflow Tracking Server**:

```bash
kubectl -n mlflow port-forward svc/mlflow-mlflow 5000:5000
```

Access: [http://localhost:5000](http://localhost:5000)

- **Prometheus PushGateway**:

```bash
kubectl -n monitoring port-forward svc/pushgateway-prometheus-pushgateway 9091:9091
```

Access: [http://localhost:9091](http://localhost:9091)

---

## 🧪 Run Experiment

1. Create a Python virtual environment and install dependencies:

    ```bash
    cd experiments
    pip install -r requirements.txt
    ```

2. Run the training script:

    ```bash
    python train_and_push.py
    ```

The script will:
    - Train a Logistic Regression model on the Iris dataset
    - Log parameters, metrics, and the model in MLflow
    - Push `mlflow_accuracy` and `mlflow_loss` metrics to Prometheus PushGateway
    - Save the best model locally in `best_model/`

---

## 📊 Explore Metrics

- **MLflow UI**:
  [http://localhost:5000](http://localhost:5000)
  Browse experiments, parameters, metrics, and artifacts.

---

## ⚙️ Notes

- To use **Bitnami OCI charts** in Argo CD, you must enable support:

  ```yaml
  data:
    helm.oci.enabled: "true"
  ```

- If pulling from private DockerHub/OCI registries, configure `imagePullSecrets`.
