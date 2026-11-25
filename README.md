# DevOps Project 2: Local Kubernetes Platform with Kind

A multi-phase, portfolio-grade local Kubernetes platform built on **Kind (Kubernetes in Docker)** with **NGINX Ingress**, **Metrics Server + HPA**, custom **Helm** charts, a **two-tier Flask + PostgreSQL microservice**, **Prometheus + Grafana** observability, and **ArgoCD** GitOps.

---

## Architecture Overview

- **Cluster (`dev-cluster`)**: 3-node Kind cluster (`1` control-plane + `2` worker nodes) configured in `kind-config.yaml` with `ingress-ready=true` and host ports `80`/`443` mapped.
- **Ingress & Autoscaling**: NGINX Ingress Controller routing `.localtest.me` domains and `localhost`, paired with Kubernetes Metrics Server (`--kubelet-insecure-tls` for Kind) and Horizontal Pod Autoscalers (`autoscaling/v2`).
- **Workloads**:
  - `test-nginx`: Baseline 2-replica Nginx deployment (`manifests/test-nginx.yaml`) with Ingress and HPA.
  - `demo-app`: Custom Helm chart (`charts/demo-app/`) rendering a ConfigMap-backed web page, Service, Ingress, and HPA.
  - `task-api`: Flask + Gunicorn REST API (`app/`) backed by PostgreSQL `16-alpine` with a `1Gi` `standard` (`rancher.io/local-path`) PersistentVolumeClaim, `/healthz` probes, and `/metrics` Prometheus instrumentation (`charts/task-api/`).
- **Observability**: `kube-prometheus-stack` (Prometheus Operator, Prometheus, kube-state-metrics, node-exporter, and Grafana) scraping cluster and `task-api` `ServiceMonitor` metrics.
- **GitOps**: ArgoCD (`argo/argo-cd`) syncing `gitops-demo-app` (`gitops/gitops-demo-app.yaml`) automatically from an in-cluster Git daemon (`gitops/git-server.yaml`).

---

## Repository Structure

```text
.
├── app/                                  # Task API Flask microservice source & Dockerfile
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── charts/
│   ├── demo-app/                         # Reusable Helm chart (ConfigMap, Deploy, Svc, Ingress, HPA)
│   └── task-api/                         # Two-tier Helm chart (Task API + PostgreSQL + PVC + ServiceMonitor)
├── gitops/
│   ├── git-server.yaml                   # In-cluster Git daemon for local ArgoCD syncing
│   └── gitops-demo-app.yaml              # ArgoCD Application manifest (auto-sync + self-heal)
├── manifests/
│   ├── hpa-test-nginx.yaml               # HPA for test-nginx
│   ├── test-nginx-ingress.yaml           # Ingress for test-nginx
│   ├── test-nginx.yaml                   # Phase 1 Nginx Deployment & Service
│   └── platform/
│       ├── argocd-values.yaml            # Helm values for ArgoCD
│       ├── ingress-node-selector-patch.yaml
│       ├── metrics-server.yaml           # Metrics Server manifest with --kubelet-insecure-tls
│       └── monitoring-values.yaml        # Helm values for kube-prometheus-stack
├── kind-config.yaml                      # 3-node Kind cluster definition
├── devopsproject2.md                     # Detailed phase guide & command cheat sheet
├── .gitignore
└── README.md
```

---

## Prerequisites

- **Docker Desktop** (running)
- **Kind** (`v0.33.0+`)
- **kubectl** (`v1.36.1+`)
- **Helm** (`v4.3.0+`)

---

## Quick Start

### Phase 1: Cluster & Baseline App
```powershell
kind create cluster --name dev-cluster --config kind-config.yaml
kubectl apply -f manifests/test-nginx.yaml
kubectl get nodes -o wide
```

### Phase 2: Platform Core (Ingress, Metrics Server, Helm)
```powershell
# Install NGINX Ingress Controller and pin to control-plane port mappings
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl patch deployment ingress-nginx-controller -n ingress-nginx --patch-file manifests/platform/ingress-node-selector-patch.yaml

# Install Metrics Server, Ingress, and HPA
kubectl apply -f manifests/platform/metrics-server.yaml
kubectl apply -f manifests/test-nginx-ingress.yaml
kubectl apply -f manifests/hpa-test-nginx.yaml

# Deploy custom Helm chart
helm upgrade --install demo-app ./charts/demo-app --wait
```

### Phase 3: Microservice + DB, Monitoring, and ArgoCD GitOps
```powershell
# Build and load the Task API image into Kind
docker build -t task-api:1.0.1 ./app
kind load docker-image task-api:1.0.1 --name dev-cluster

# Install Prometheus & Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack `
  --namespace monitoring --create-namespace -f manifests/platform/monitoring-values.yaml --wait

# Deploy Task API + PostgreSQL + ServiceMonitor
helm upgrade --install task-api ./charts/task-api --wait

# Install ArgoCD & deploy GitOps Application
helm upgrade --install argocd argo/argo-cd `
  --namespace argocd --create-namespace -f manifests/platform/argocd-values.yaml --wait
kubectl apply -f gitops/git-server.yaml
kubectl apply -f gitops/gitops-demo-app.yaml
```

---

## Live Endpoints (`.localtest.me` -> `127.0.0.1`)

| Service | URL | Notes |
|---|---|---|
| **Nginx Test App** | `http://localhost/` | Baseline Nginx workload |
| **Helm Demo App** | `http://demo.localtest.me/` | Deployed via `charts/demo-app` |
| **Task API** | `http://task-api.localtest.me/` | Endpoints: `/healthz`, `/tasks`, `/metrics` |
| **Grafana** | `http://grafana.localtest.me/` | Local demo credentials configured in `monitoring-values.yaml` |
| **ArgoCD UI** | `http://argocd.localtest.me/` | Retrieve password via `argocd-initial-admin-secret` |
| **GitOps Demo App** | `http://gitops-demo.localtest.me/` | Managed automatically by ArgoCD |

### Test the Task API
```powershell
Invoke-RestMethod http://task-api.localtest.me/healthz
Invoke-RestMethod -Uri http://task-api.localtest.me/tasks -Method Post -ContentType 'application/json' -Body '{"title":"Hello Kubernetes"}'
Invoke-RestMethod http://task-api.localtest.me/tasks
```

> **Note:** Default credentials in `charts/task-api/values.yaml` and `manifests/platform/monitoring-values.yaml` are for local Kind development only—replace them before deploying to shared or production environments.
