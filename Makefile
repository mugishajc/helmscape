SERVICES := catalog-service orders-service users-service

.PHONY: lint test build helm-lint kustomize-build

lint:
	@for svc in $(SERVICES); do \
		echo "--- ruff check services/$$svc"; \
		cd services/$$svc && python -m ruff check app/ tests/ && cd ../..; \
	done

test:
	@for svc in $(SERVICES); do \
		echo "--- pytest services/$$svc"; \
		cd services/$$svc && python -m pytest -q && cd ../..; \
	done

build:
	@for svc in $(SERVICES); do \
		echo "--- docker build services/$$svc"; \
		docker build -t ghcr.io/mugishajc/$$svc:local services/$$svc; \
	done

helm-lint:
	@for svc in $(SERVICES); do \
		echo "--- helm lint helm/$$svc"; \
		helm lint helm/$$svc; \
	done

kustomize-build:
	@for env in staging production; do \
		echo "--- kustomize build k8s/overlays/$$env"; \
		kubectl kustomize k8s/overlays/$$env > /dev/null; \
	done
	@echo "All overlays build cleanly."
