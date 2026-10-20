# Productionized Legacy Application (DevSecOps)

[![Node.js](https://img.shields.io/badge/Node.js-Express-339933?logo=nodedotjs)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Multi--stage-2496ED?logo=docker)](https://docker.com/)
[![Trivy](https://img.shields.io/badge/Trivy-Security-008080)](https://aquasecurity.github.io/trivy/)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI/CD-2088FF?logo=github-actions)](https://github.com/features/actions)

A portfolio project demonstrating practical **Brownfield DevSecOps** and **Release Engineering**. 

The premise: I inherited a deliberately minimal "legacy" Node.js inventory application. This subtree is currently a **reference workload** for release engineering, GitOps, and SRE validation: its `/sync` endpoint is a no-op simulation and does **not** persist or synchronize inventory. Instead of presenting it as a complete inventory product, this phase productionizes how the workload builds, runs, and deploys—transforming a fragile script into a secure, observable, and immutable release artifact.

> **Scope boundary:** A real inventory-sync product requires a versioned integration contract, service authentication, durable idempotency, persistence/outbox, and failure-recovery tests. Those capabilities are intentionally not claimed by this reference workload and are tracked as a later enterprise-pilot phase.

## 🚀 Engineering Highlights

- **Containerization Hygiene:** Introduced a multi-stage Docker build resulting in a minimal, secure image running as a **non-root user**. Added explicit `HEALTHCHECK`, structured JSON logging, and graceful shutdown (draining connections on `SIGTERM`).
- **DevSecOps Blocking Gate:** Converted Trivy from a mere advisory tool into a strict **blocking CI gate**. The pipeline halts on Critical/High CVEs in the filesystem, IaC, and container image, enforcing a baseline security policy before merging.
- **Release Contract:** Implemented a robust GitHub Actions pipeline leveraging **Azure OIDC** for secretless authentication. Images are built immutably as `legacy-app:<git-sha>`, pushed to Azure Container Registry (ACR) with digest verification, and automatically pinned via GitOps.
- **Smart CI Executions:** Added runtime change detection to ensure that documentation-only commits (like updating this README) do not trigger expensive application image builds.

## 🛠️ The Pipeline

```mermaid
flowchart LR
    Commit[Git Commit] --> Build[Docker Build]
    Build --> Scan[Trivy Vulnerability Scan]
    Scan -- Pass --> Push[OIDC Push to ACR]
    Push --> Tag[GitOps Image Pinning]
    Scan -- Fail (CRITICAL/HIGH) --> Block((Pipeline Fails))
```

## 📂 Project Structure

```text
src/
├── server.js              # Entry point: listen + graceful shutdown
├── app.js                 # Composition root (wiring, no logic)
├── routes/                # HTTP layer (health checks, mapping)
├── services/              # Legacy Business logic
├── middleware/            # Error handling, JSON logging
└── test/                  # Node.js smoke tests
Dockerfile                 # Multi-stage, non-root, minimal surface
.github/workflows/         # CI/CD and Trivy DevSecOps pipelines
```
