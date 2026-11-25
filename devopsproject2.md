/# DevOps Project 2: Kubernetes Local Cluster with Kind

This document contains setup instructions, configuration templates, and essential commands to resume your work with **Kind** (Kubernetes in Docker).

---

## 1. System Status & Prerequisites

As of your initial setup:
- **Docker**: Installed & Running (Docker Desktop)
- **kubectl**: Installed (`v1.36.1`)
- **kind**: Installed (`v0.33.0`) via Winget

---

## 2. Step 1: Refresh Terminal Environment (If `kind` command not found)

If you open a new PowerShell window and `kind` isn't recognized, run:

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

Verify installation:
```powershell
kind --version
```

---

## 3. Step 2: Create a Local Kubernetes Cluster

Make sure Docker Desktop is running before executing these commands.

### Option A: Quick Single-Node Cluster (Default)
```powershell
kind create cluster --name dev-cluster
```

### Option B: Multi-Node Cluster (Control-Plane + 2 Worker Nodes)
Create a file named `kind-config.yaml`:

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
```

Create the cluster using the configuration:
```powershell
kind create cluster --name dev-cluster --config kind-config.yaml
```

---

## 4. Step 3: Verify the Cluster

Kind automatically switches your `kubectl` context to the newly created cluster.

```powershell
# 1. Verify cluster connection
kubectl cluster-info

# 2. View nodes and their status
kubectl get nodes -o wide

# 3. View all running system pods
kubectl get pods -A
```

---

## 5. Step 4: Deploy a Test Application (Nginx)

```powershell
# 1. Create an Nginx deployment
kubectl create deployment test-nginx --image=nginx:alpine

# 2. Expose deployment as a Service
kubectl expose deployment test-nginx --port=80 --type=NodePort

# 3. Check deployment and service status
kubectl get deployments
kubectl get services

# 4. Port forward to access on localhost
kubectl port-forward service/test-nginx 8080:80
```
Open your browser and navigate to: `http://localhost:8080`

---

## 6. Kind & Kubectl Command Cheat Sheet

| Action | Command |
|---|---|
| **List Kind clusters** | `kind get clusters` |
| **Delete a cluster** | `kind delete cluster --name dev-cluster` |
| **Check current context** | `kubectl config current-context` |
| **Switch context** | `kubectl config use-context kind-dev-cluster` |
| **View node resource usage** | `kubectl top nodes` *(requires metrics-server)* |
| **Get all pods in namespace** | `kubectl get pods` |
| **Describe a pod (troubleshooting)**| `kubectl describe pod <pod-name>` |
| **View pod logs** | `kubectl logs <pod-name>` |

---

## 7. Phase 2 Artifacts & Commands (Platform Core)

- **NGINX Ingress Controller**:
  - Installed from the Kind provider manifest and patched with [manifests/platform/ingress-node-selector-patch.yaml](manifests/platform/ingress-node-selector-patch.yaml) (`ingress-ready: "true"`) so it schedules on `dev-cluster-control-plane` (ports `80`/`443`).
  - Ingress for `test-nginx`: [manifests/test-nginx-ingress.yaml](manifests/test-nginx-ingress.yaml) (`http://localhost/`).
- **Metrics Server & HPA**:
  - Manifest saved in [manifests/platform/metrics-server.yaml](manifests/platform/metrics-server.yaml) with `--kubelet-insecure-tls` enabled for Kind.
  - HPA for `test-nginx`: [manifests/hpa-test-nginx.yaml](manifests/hpa-test-nginx.yaml) (`minReplicas: 2`, `maxReplicas: 5`, target CPU `50%`).
  - Verify metrics: `kubectl top nodes`, `kubectl top pods -A`, `kubectl get hpa`.
- **Helm Chart (`demo-app`)**:
  - Chart located at [charts/demo-app/](charts/demo-app/Chart.yaml) (ConfigMap, Deployment, ClusterIP Service, Ingress for `demo.localtest.me`, and HPA).
  - Deploy/upgrade: `helm upgrade --install demo-app ./charts/demo-app`

---

## 8. Next Steps for DevOps / Platform Practice (Phase 3)
1. **Microservice App + DB**: Deploy a multi-tier service with persistent storage (`local-path` StorageClass).
2. **GitOps (ArgoCD)**: Install ArgoCD and manage cluster manifests/charts declaratively via Git.
3. **Observability**: Install Prometheus + Grafana (`kube-prometheus-stack` via Helm) for cluster and app monitoring.

---

## 9. Project Roadmap & Time Estimates

| Phase | Scope | Estimated Time | Status |
|---|---|---|---|
| **Phase 1: Basic Cluster & Pods** | • 3-node Kind cluster<br>• Deploy Nginx test app & port-forward | ~15 mins | ✅ **Completed** |
| **Phase 2: Platform Core** | • NGINX Ingress controller<br>• Metrics Server + HPA (autoscaling)<br>• Helm chart deployment | ~1-2 hours | ✅ **Completed** |
| **Phase 3: Portfolio / Production Grade** | • Microservice app + DB<br>• ArgoCD (GitOps)<br>• Prometheus + Grafana monitoring | ~3-4 hours | ⏳ **Ready to start next** |

> **Checkpoint**: Phase 2 is complete. NGINX Ingress Controller (`localhost` & `demo.localtest.me`), Metrics Server (`kubectl top` + HPAs), and the `demo-app` Helm release are all running and verified on `dev-cluster`. When ready to resume, begin **Phase 3: Portfolio / Production Grade** (Microservice + DB, ArgoCD GitOps, and Prometheus + Grafana).

