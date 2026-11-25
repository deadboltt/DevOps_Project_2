CLUSTER_NAME ?= dev-cluster
IMAGE_TAG ?= 1.0.2
DB_PASSWORD ?=

.PHONY: help lint test build load cluster deploy-platform deploy-app verify clean

help:
	@echo "Available targets:"
	@echo "  lint             - Lint Python code and Helm charts"
	@echo "  test             - Run Task API unit tests"
	@echo "  build            - Build task-api:$(IMAGE_TAG) container image"
	@echo "  load             - Load task-api:$(IMAGE_TAG) into Kind cluster"
	@echo "  cluster          - Create 3-node Kind cluster ($(CLUSTER_NAME))"
	@echo "  deploy-platform  - Install NGINX Ingress, Metrics Server, Monitoring, and ArgoCD"
	@echo "  deploy-app       - Deploy demo-app and task-api (requires DB_PASSWORD=...)"
	@echo "  verify           - Run cluster & HTTP endpoint verification"
	@echo "  clean            - Delete Kind cluster $(CLUSTER_NAME)"

lint:
	ruff check app
	helm lint charts/demo-app
	helm lint charts/task-api --set postgres.password=lint-only

test:
	PYTHONPATH=app pytest -v app/tests

build:
	docker build -t task-api:$(IMAGE_TAG) ./app

load:
	kind load docker-image task-api:$(IMAGE_TAG) --name $(CLUSTER_NAME)

cluster:
	kind create cluster --name $(CLUSTER_NAME) --config kind-config.yaml

deploy-platform:
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
	kubectl patch deployment ingress-nginx-controller -n ingress-nginx --patch-file manifests/platform/ingress-node-selector-patch.yaml
	kubectl apply -f manifests/platform/metrics-server.yaml
	helm upgrade --install monitoring prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace -f manifests/platform/monitoring-values.yaml --wait
	helm upgrade --install argocd argo/argo-cd --namespace argocd --create-namespace -f manifests/platform/argocd-values.yaml --wait

deploy-app:
	@test -n "$(DB_PASSWORD)" || (echo "Error: pass DB_PASSWORD=<value>" && exit 1)
	helm upgrade --install demo-app ./charts/demo-app --wait
	helm upgrade --install task-api ./charts/task-api --set postgres.password=$(DB_PASSWORD) --wait

verify:
	kubectl get nodes,pods,ingress -A
	helm list -A

clean:
	kind delete cluster --name $(CLUSTER_NAME)
