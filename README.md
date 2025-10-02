# goitneo-argo

This repository contains Kubernetes namespaces and an ArgoCD Application manifest for deploying Nginx using the Bitnami Helm chart.

---

## 📂 Structure

```bash
goit-argo
├── application.yaml
├── namespaces
│  ├── application
│  │  ├── ns.yaml
│  │  └── nginx.yaml
│  └── infra-tools
│     └── ns.yaml
└── README.md
```

---

## ⚙️ Prerequisites

- An existing EKS (or any Kubernetes) cluster.
- ArgoCD installed in the `infra-tools` namespace (via Terraform or Helm).
- kubectl configured to point to the cluster.

---

## 🚀 Deployment Steps

### 1. Apply Namespaces

```bash
kubectl apply -f namespaces/infra-tools/ns.yaml
kubectl apply -f namespaces/application/ns.yaml
```

### 2. Apply ArgoCD Application

Commit and push `application.yaml` to this repository.  
ArgoCD, installed in `infra-tools` namespace, will detect and apply it automatically.

Check Application status:

```bash
kubectl get applications -n infra-tools
```

### 3. Verify Deployment

Check Nginx pods and services in the `application` namespace:

```bash
kubectl get pods -n application
kubectl get svc -n application
```

---

## 🌐 Access Nginx Service

Since the Nginx service is of type `ClusterIP`, use port-forwarding to access it locally:

```bash
kubectl port-forward svc/nginx -n application 8080:80
```

Open in your browser:

```bash
http://localhost:8080
```

You should see the default Nginx welcome page.

---

## 🔑 Useful Commands

- Get ArgoCD Application details:

```bash
kubectl describe application nginx-demo -n infra-tools
```

- Force sync an Application:

```bash
kubectl argocd app sync nginx-demo -n infra-tools
```

- Delete the Nginx Application:

```bash
kubectl delete application nginx-demo -n infra-tools
```

---

## ✅ Expected Outcome

- Namespaces `infra-tools` and `application` are created.
- ArgoCD deploys Nginx using the Bitnami Helm chart with provided values.
- Nginx pods and service appear in the `application` namespace.
- Nginx is accessible locally via `kubectl port-forward`.
