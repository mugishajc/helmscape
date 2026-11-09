# cloud-native-gitops-demo

A small reference of how I ship a service to Kubernetes. Two Python microservices, containerised, packaged as Helm charts, deployed through Argo CD with the app-of-apps pattern, images built and pushed by GitHub Actions on every push to `main`.

Everything here is working code you can run end to end.

## What is in the repo

```
services/
  catalog-service/   FastAPI item catalog with pytest and a Dockerfile
  orders-service/    FastAPI orders API that calls the catalog, with tests
k8s/
  base/              Kustomize base: Deployments, Services, HPA, Namespace
  overlays/          Per-environment overlays for staging and production
helm/
  catalog-service/   Helm chart for the catalog service
  orders-service/    Helm chart for the orders service
argocd/
  app-of-apps.yaml   Root Argo CD Application
  apps/              One Argo CD Application per environment
.github/workflows/
  ci.yml             Tests, kubeconform, helm lint on every PR
  build-and-push.yml Multi-arch images to GHCR on push to main
docker-compose.yml   Run both services locally
```

## The services

Two small FastAPI services with `/healthz`, `/readyz` and `/metrics` endpoints. Orders calls Catalog to look up prices before persisting an order. In-memory stores keep the example focused on the delivery pipeline, not the database layer.

Run the tests:

```bash
cd services/catalog-service && pip install -e .[dev] && pytest -q
cd services/orders-service   && pip install -e .[dev] && pytest -q
```

Run the pair locally:

```bash
docker compose up --build
curl -s localhost:8001/items
curl -s -X POST localhost:8002/orders -H 'content-type: application/json' \
     -d '{"item_id": 1, "quantity": 3}'
```

## Kubernetes with Kustomize

`k8s/base` has the shared Deployments, Services, HorizontalPodAutoscaler and Namespace. Each environment overlay patches replica counts and image tags. Preview what will be applied:

```bash
kubectl kustomize k8s/overlays/staging
kubectl kustomize k8s/overlays/production
```

Hardening defaults used in every Pod: `runAsNonRoot`, read-only root filesystem, `drop: [ALL]` capabilities, resource requests and limits, RuntimeDefault seccomp.

## Helm charts

Same workloads packaged as charts so they can be installed with a single command:

```bash
helm install orders  ./helm/orders-service
helm install catalog ./helm/catalog-service
```

Typical overrides (replicas, image tag, resources, autoscaling) live in `values.yaml`.

## Argo CD (GitOps)

The cluster is the source of truth for what is running. Git is the source of truth for what should be running. Argo CD reconciles the two.

```bash
kubectl apply -n argocd -f argocd/app-of-apps.yaml
```

`shop-root` points Argo CD at `argocd/apps/`, where one Application per environment points at the corresponding Kustomize overlay. Staging is set to automated sync with prune and self-heal. Production is manual by default: once a staging soak is clean, promote by changing the image tag in `k8s/overlays/production/kustomization.yaml` and merging.

## CI/CD

`ci.yml` runs on every PR:
- `pytest` for each service
- `kubeconform` on both overlays
- `helm lint` on each chart

`build-and-push.yml` runs on `main`:
- builds each service image with Buildx
- pushes to `ghcr.io/mugishajc/<service>` tagged with the commit SHA and `latest`

To cut a release: bump `appVersion` in each chart, bump `newTag` in the overlays, commit, and Argo CD rolls it out.

## Why this shape

- Kustomize for infrastructure differences between environments, Helm for packaging a single service.
- App of apps so adding an environment is one file in `argocd/apps/`, not a cluster change.
- Images pinned by SHA in overlays rather than mutable tags, so a rollback is a git revert.
- Prometheus annotations on Pods so scraping is opt-in and visible in the manifest.
