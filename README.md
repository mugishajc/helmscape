# helmscape

Microservices on Kubernetes. Three Python services, containerised, packaged as Helm charts and Kustomize overlays, deployed through Argo CD with the app-of-apps pattern. GitHub Actions builds and pushes images on every merge to `main`.

Everything here is working code you can run end to end.

## Repository layout

```
services/
  catalog-service/   FastAPI item catalog
  orders-service/    FastAPI orders API (calls catalog-service for prices)
  users-service/     FastAPI user account management
helm/
  catalog-service/   Helm chart with HPA and configurable values
  orders-service/    Helm chart with HPA and configurable values
  users-service/     Helm chart with HPA and configurable values
k8s/
  base/              Kustomize base: Deployments, Services, HPAs, NetworkPolicies, Namespace
  overlays/          Per-environment overlays (staging, production)
argocd/
  app-of-apps.yaml   Root Argo CD Application
  apps/              One Argo CD Application per environment
monitoring/
  *-service-monitor.yaml   ServiceMonitor CRDs for Prometheus scraping
docs/
  architecture.md    Architecture overview
.github/workflows/
  ci.yml             Tests + kubeconform + helm lint on every PR
  build-and-push.yml Multi-arch images to GHCR on push to main
docker-compose.yml   Run all three services locally
Makefile             lint, test, build, helm-lint, kustomize-build
```

## Services

Three FastAPI services, each with `/healthz`, `/readyz`, and `/metrics` endpoints.

| Service | Purpose | Dependencies |
|---------|---------|--------------|
| catalog-service | Item lookup (name, price) | None |
| orders-service | Order creation with price resolution | catalog-service |
| users-service | User CRUD with email validation | None |

In-memory stores keep the example focused on the delivery pipeline, not the database layer.

## Quick start

Run all services locally:

```bash
docker compose up --build
curl -s localhost:8001/items
curl -s -X POST localhost:8002/orders -H 'content-type: application/json' \
     -d '{"item_id": 1, "quantity": 3}'
curl -s -X POST localhost:8003/users -H 'content-type: application/json' \
     -d '{"name": "Alice", "email": "alice@example.com"}'
```

Run tests:

```bash
make test
```

Or per-service:

```bash
cd services/catalog-service && pip install -e .[dev] && pytest -q
```

## Kubernetes with Kustomize

`k8s/base/` has Deployments, Services, HorizontalPodAutoscalers, NetworkPolicies, and a Namespace. Each environment overlay patches replica counts and image tags.

```bash
kubectl kustomize k8s/overlays/staging
kubectl kustomize k8s/overlays/production
```

### NetworkPolicies

A default-deny policy blocks all traffic. Per-service policies open only the required paths:

- orders-service can reach catalog-service on port 8000
- catalog-service accepts ingress only from orders-service and from the monitoring namespace
- users-service accepts external ingress only
- All services allow DNS egress

### Autoscaling

Every service has an HPA targeting 70% CPU, scaling between 2 and 6 replicas.

## Helm charts

```bash
helm install catalog ./helm/catalog-service
helm install orders  ./helm/orders-service
helm install users   ./helm/users-service
```

Each chart supports replica count, image, resources, and autoscaling overrides through `values.yaml`.

## Argo CD (GitOps)

Git is the source of truth for what should be running. Argo CD reconciles the cluster to match.

```bash
kubectl apply -n argocd -f argocd/app-of-apps.yaml
```

`shop-root` points at `argocd/apps/`, where one Application per environment references the matching Kustomize overlay. Staging syncs automatically with prune and self-heal. Production is manual: promote by updating the image tag and merging.

## Monitoring

ServiceMonitor CRDs in `monitoring/` tell Prometheus (kube-prometheus-stack) to scrape `/metrics` on each service every 30 seconds.

## CI/CD

**ci.yml** (every PR): pytest per service, kubeconform on both overlays, helm lint on every chart.

**build-and-push.yml** (push to main): multi-arch Docker images to `ghcr.io/mugishajc/<service>`, tagged with commit SHA and `latest`.

To cut a release: bump `appVersion` in each chart, bump `newTag` in the overlays, commit, and Argo CD rolls it out.

## Makefile targets

| Target | What it does |
|--------|-------------|
| `make lint` | Runs ruff on all service code |
| `make test` | Runs pytest for each service |
| `make build` | Builds Docker images locally |
| `make helm-lint` | Lints all Helm charts |
| `make kustomize-build` | Validates both Kustomize overlays |

## Security defaults

Every Pod enforces: `runAsNonRoot`, read-only root filesystem, `drop: [ALL]` capabilities, resource requests/limits, RuntimeDefault seccomp profile.

## Why this shape

- Kustomize for infrastructure differences between environments, Helm for packaging a single service.
- App of apps so adding an environment is one file in `argocd/apps/`, not a cluster change.
- Images pinned by SHA in overlays rather than mutable tags, so a rollback is a git revert.
- Prometheus annotations on Pods so scraping is opt-in and visible in the manifest.
