# Curriculum Vitae — Senior DevOps / Platform / SRE Engineer

**Candidate:** Mai Nguyễn Bình Tân  
**Focus:** Kubernetes platform engineering, GitOps automation, resilience drills under load, disaster recovery automation, and policy-as-code governance.  
**Core Technologies:** Kubernetes (v1.36.1 / Kind), Argo CD (v3.5.5), Envoy Gateway (v1.9.1 / Gateway API), Terraform, Helm, Kustomize, Docker, Prometheus, Grafana, Bash, Python 3.11, GitHub Actions.

---

## Executive Summary
Platform / DevOps / SRE Engineer with solid experience in container orchestration, GitOps delivery pipelines, north-south traffic routing, and empirical reliability testing. Proven ability to establish reproducible Kubernetes platform golden paths, automate database backup and cold restoration drills, measure rolling update availability under continuous synthetic probe traffic, and enforce shift-left policy gates in CI/CD.

---

## Demonstrated Technical Achievements (Evidence-Backed)

### 1. Kubernetes GitOps Golden Path & Gateway API Ingress (`platform/aks-sre-platform`)
*Stack: Kubernetes v1.36.1, Argo CD v3.5.5, Envoy Gateway v1.9.1, Kustomize, Kind.*
- **GitOps Delivery Engine:** Bootstrapped pinned Argo CD (v3.5.5) using server-side apply to eliminate the upstream 256 KiB CRD annotation limit. Configured AppProject and Application manifests to reconcile workloads directly from Git with automated self-healing.
- **Shared North-South Gateway API Routing:** Architected north-south ingress using Envoy Gateway v1.9.1 and Gateway API HTTPRoute objects. Formulated route isolation across independent application domains through a single shared platform Gateway, with unmatched hosts safely returning HTTP 404 (`scripts/demo-local-platform.sh`).
- **Digest Pinning Architecture:** Formulated immutable container digest references (`@sha256:...`) across deployment manifests to eliminate configuration drift and accidental mutable tag overwrites.

### 2. Empirical Rollout & Rollback Resilience Drill
*Target: Order.Api Deployment (2 replicas) on Kind cluster*
- **Continuous Traffic Probe:** Designed high-frequency probing harness (20 req/s) transmitting 162 HTTP requests continuously during active rolling updates and fault injection (`scripts/test_zero_downtime_rollback_drill.sh`).
- **Fault Containment:** Injected broken deployment (non-existent image tag). Kubernetes rolling update stalled the rollout while existing healthy replicas absorbed 100% of incoming traffic without a single dropped packet during the test window.
- **Sub-Second Automated Rollback (Kind Cluster Probe Harness):** Triggered deployment rollback (`rollout undo`) under Kind test harness, achieving clean recovery in **509.23 ms** with **100.00% empirical availability** (162/162 HTTP 200 OK, 0 errors, 0 dropped requests, p95 latency 14.09 ms).

### 3. Database Disaster Recovery (DR) & RTO/RPO Drill
*Target: Live Application Database (`FlashSaleDb` on PostgreSQL 15 in Kind cluster)*
- **Catastrophic Failure Injection:** Executed automated disaster drill (`scripts/real_workload_dr_drill.sh`) by forcefully dropping the live application database (`DROP DATABASE "FlashSaleDb" WITH (FORCE)`).
- **Sub-Second Database Restore Time (Cold Kind Test Harness):** Orchestrated automated database recreation and cold restore from a 60,482-byte binary snapshot under local Kind test harness. Application resumed healthy HTTP 200 OK operations with a total measured **RTO of 0.570 seconds** (569.98 ms; database restore in 333.25 ms).
- **Cold Snapshot Parity Verification:** Validated exact cryptographic MD5 parity before disaster and after restoration across 57 orders (`a8d59f33a7c0792523de33de8bd4d520`) and 11 inventory products (`9b26695d62ffcac0ae1604649f4ff156`). Analyzed trade-offs: cold snapshots without WAL streaming inevitably lose delta transactions occurring between snapshot time and disaster time (`docs/evidence/real-workload-dr-drill-PASS.md`).

### 4. SRE Observability & Automated Alert Lifecycle
*Stack: Prometheus Operator, kube-prometheus-stack v91.5.0, Grafana, PrometheusRule.*
- **Cluster Observability Stack:** Deployed Prometheus (27 active scrape targets) and Grafana (26 provisioned dashboards covering workloads, ingress, nodes, and GitOps state).
- **Alert Fire & Auto-Resolve Drill:** Implemented real PrometheusRule `LocalPlatformMetricSourceDown`. Proved automated failure detection by scaling metric sources to zero (transition to FIRING within 35s), followed by automatic resolution upon replica restoration (`/tmp/test-alert-fire-resolve.sh`).

### 5. Shift-Left CI Policy Gates & Infrastructure-as-Code
*Stack: Python 3.11, Terraform, TFLint, GitHub Actions*
- **Automated CI Policy Enforcement:** Implemented 14 strict validation gates (47 assertions total in `tests/test_gates.py`) validating manifest inventories, orphan detection, Argo CD AppProject namespace allowlists, and pinned versions (`platform/argocd/VERSION`).
- **Protected Environment Governance:** Configured GitHub protected environment `production` with required manual reviewer approval (`imtarget05`), ensuring cloud mutations and production deployments require human sign-off.
- **Monorepo Unified CI Matrix:** Built unified GitHub Actions pipeline (`.github/workflows/monorepo-ci.yml`) coordinating parallel verification of 4 polyglot workloads (Java, .NET, Python, Platform) with path-based change detection (`dorny/paths-filter`).

---

## Technical Competencies
- **Container & Cluster Orchestration:** Kubernetes (v1.36.1), Kind, Docker, Containerd, Envoy Gateway (Gateway API).
- **GitOps & Delivery:** Argo CD (v3.5.5), Kustomize, Helm, GitHub Actions, Bash Scripting.
- **Infrastructure as Code:** Terraform, TFLint, Policy Gates, Server-Side Apply.
- **Observability & SRE:** Prometheus, Grafana, OpenTelemetry, SLI/SLO Baseline Measurement, PDB & Node Drain Drills, Alert Fire/Resolve Drills.
- **Security & Hardening:** Pod Security Standards, Non-Root Workloads, Read-Only Filesystems, Trivy Vulnerability Scanning.
