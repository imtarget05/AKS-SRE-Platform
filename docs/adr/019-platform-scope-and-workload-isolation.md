# ADR 019: Platform Scope, Responsibility Boundaries, and Workload Isolation

## Status
Accepted

## Context
As the platform evolved, various demo and experimental workloads (e.g. `apps/agent-hub`, `apps/legacy-inventory`, `apps/sre-console`) were placed in the `apps/` directory of the `AKS-SRE-Platform` repository. Without clear architectural boundaries, the SRE Platform risk being conflated with application business logic, muddying the definition of "Platform as a Product".

## Decision
1. **Core Platform Scope ("Platform as a Product")**:
   - Reusable Infrastructure as Code (`terraform/`): Azure resource groups, virtual networks, Key Vault, AKS cluster, managed identities.
   - Kubernetes Platform Engine (`platform/`):
     - GitOps Controller (Argo CD) & AppProjects (`portfolio`).
     - Ingress / Gateway: Envoy Gateway, Gateway API, and Cloudflare Edge Worker mTLS termination.
     - Observability Stack: Prometheus, Grafana, OpenTelemetry collectors, ServiceMonitors, and cluster-wide alerts.
     - Security & Policy: Non-root execution, PodDisruptionBudgets, network policies, rate-limiting.
2. **Workload Ownership & Self-Service Contracts**:
   - Workloads (`FlashSale-Backend`, `QuanLyKho`) are standalone products that own their source code, build pipelines, Dockerfiles, and database schemas.
   - Workloads own their release manifests (`overlays/production` or `overlays/azure-cloud`) and Argo CD Application manifests.
   - The platform repository manages registration, authorization in AppProjects, and baseline cluster resources.
3. **Optional / Experimental Tooling Isolation**:
   - `apps/agent-hub` and other experimental tools are strictly opt-in and non-blocking for platform delivery.
   - Experimental tools MUST NOT be required dependencies for deploying core workloads.
   - Neither FlashSale nor QuanLyKho depends on `agent-hub` or `legacy-inventory` to function correctly.

## Consequences
- **Positive**:
  - The SRE platform can onboard new 3rd-party applications in the future through standard golden path contracts without re-architecting the platform.
  - Clear ownership boundaries between SRE/Platform engineers and Application/Backend developers.
  - Zero blast-radius between applications: FlashSale and QuanLyKho run with isolated databases, secrets, and lifecycles.
