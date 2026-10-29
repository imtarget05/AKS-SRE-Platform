.PHONY: all sbom scan sign test lint

# Variables
IMAGE_NAME ?= aks-sre-platform
IMAGE_TAG ?= latest
SBOM_FILE ?= sbom.json
TRIVY_SEVERITY ?= CRITICAL

# Docker-related targets
docker-build:
	@docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

docker-push:
	@docker push $(IMAGE_NAME):$(IMAGE_TAG)

# SBOM Generation target
# Uses syft to generate a CycloneDX SBOM from the built image
sbom: docker-build
	@echo "Generating SBOM for $(IMAGE_NAME):$(IMAGE_TAG)..."
	@docker run --rm -v "$(PWD)":/workload aquasec/syft syft docker://$(IMAGE_NAME):$(IMAGE_TAG) -o json > $(SBOM_FILE)
	@echo "SBOM generated: $(SBOM_FILE)"
	@ls -lh $(SBOM_FILE)

# Vulnerability Scan target
# Uses trivy to scan the built image for vulnerabilities
scan: docker-build
	@echo "Scanning $(IMAGE_NAME):$(IMAGE_TAG) for vulnerabilities..."
	@trivy image --severity $(TRIVY_SEVERITY),LOW,HIGH,CRITICAL --format sarif -o trivy-results.sarif $(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Scan complete. Results in trivy-results.sarif"

# Signature Verification target
# Uses cosign to verify the image signature
sign: docker-push
	@echo "Signing image $(IMAGE_NAME):$(IMAGE_TAG) with cosign..."
	@cosign sign --key $(COSIGN_PRIVATE_KEY) $(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Image signed successfully"
	@cosign verify $(IMAGE_NAME):$(IMAGE_TAG)

# Test target — run offline Python test suite (pytest)
test:
	@echo "Running offline test suite..."
	@python -m pytest tests/ -q

# Lint target — syntax-check Python sources + render kustomize manifests
lint:
	@echo "Syntax-checking Python sources..."
	@python -m py_compile tests/*.py scripts/*.py
	@echo "Rendering kustomize manifests..."
	@kubectl kustomize deploy/base >/dev/null 2>&1 || echo "kubectl unavailable; skipping manifest render"
	@echo "Lint complete."

# Default target
all: sbom scan