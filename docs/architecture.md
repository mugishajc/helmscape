# Architecture

## Services

Three Python (FastAPI) microservices sit behind a Kubernetes cluster:

- **catalog-service** -- item lookup. Returns product names and prices. No external dependencies.
- **orders-service** -- order creation. Calls catalog-service over HTTP to resolve item prices before recording an order.
- **users-service** -- account management. CRUD operations on user records with email uniqueness enforcement and input validation.

All three expose `/healthz`, `/readyz`, and `/metrics` (Prometheus client format). They run as non-root in read-only containers with dropped capabilities.

## Packaging

Each service is packaged two ways:

1. **Kustomize** (`k8s/base/` + per-environment overlays in `k8s/overlays/`). The base includes Deployments, Services, HorizontalPodAutoscalers, NetworkPolicies, and a shared Namespace. Overlays patch replica counts and image tags per environment.
2. **Helm** (`helm/<service>/`). One chart per service with configurable replicas, image, resources, and autoscaling. Same workloads, different delivery tool.

## Deployment

Argo CD drives deployments through the app-of-apps pattern:

- `shop-root` points at `argocd/apps/`, which holds one Application per environment.
- Staging syncs automatically with prune and self-heal.
- Production requires a manual sync. Promote by updating the image tag in the production overlay and merging.

## Networking

A default-deny NetworkPolicy locks down all Pod traffic. Per-service policies open only the ports each service actually needs:

- catalog-service accepts ingress from orders-service and from the monitoring namespace.
- orders-service accepts external ingress and can reach catalog-service.
- users-service accepts external ingress.
- All services allow DNS egress.

## Scaling

Each service has a HorizontalPodAutoscaler targeting 70% CPU. Staging runs 1 replica, production runs 3, and the HPA can scale up to 6.

## Monitoring

ServiceMonitor CRDs in `monitoring/` configure Prometheus (via kube-prometheus-stack) to scrape the `/metrics` endpoint on each service at 30-second intervals.

## CI/CD

GitHub Actions runs two workflows:

- **ci.yml** -- on every PR: pytest for each service, kubeconform on both Kustomize overlays, helm lint on each chart.
- **build-and-push.yml** -- on push to main: multi-arch Docker images pushed to GHCR, tagged with the commit SHA and `latest`.

## Container security defaults

Every Pod spec enforces:

- `runAsNonRoot: true`
- `readOnlyRootFilesystem: true`
- `allowPrivilegeEscalation: false`
- `capabilities: { drop: [ALL] }`
- `seccompProfile: { type: RuntimeDefault }`
- Resource requests and limits on every container
