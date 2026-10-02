# Master Evidence Index (EVIDENCE.md)

This document maps every engineering capability claim to concrete, measured runtime artifacts, reproduction commands, and Git commits. No metrics are fabricated.

## ⚠️ Read this before citing any row

Every row below was measured on a **local kind cluster**. That environment is
now the **OSS / dry-run profile**, not the proof surface
([`adr/014-azure-first-verification.md`](adr/014-azure-first-verification.md)).

| Environment label | Meaning |
|---|---|
| `PRE_AZURE_DRY_RUN` | Measured on local kind. Valid for the OSS profile. **Not** Azure evidence. |
| `AZURE_VALIDATION` | Measured on a real AKS cluster. Not yet populated — Phases E–N. |

A row is never relabelled between these. The Azure rows will be added when they
exist, with their own timestamps, commits and teardown records.

Separately, one capability *was* proven on real AKS on 2026-09-21 and is indexed
separately below, in [`evidence/phase7a/`](evidence/phase7a/) — AKS foundation,
user-pool isolation, private ACR pull by digest, and Workload Identity token
exchange.

---

## Master Claim-to-Evidence Matrix (Environment: `PRE_AZURE_DRY_RUN`)

| # | Capability Claim | Live Verification / Proof Command | Primary Evidence Document | Git Commit |
|---|---|---|---|---|
| **L0/L2** | Reproducible, pinned 3-node Kubernetes cluster on macOS arm64 without Azure | `kubectl get nodes -o wide` (3/3 Ready, v1.36.1, containerd 2.3.1) | `local/kind/README.md` | `991ec05` |
| **L1** | arm64 native container builds; containerd nested index delivery workaround | `./local/kind/load-image.sh <image>` with `--platform linux/arm64` export | `docs/evidence/local-platform/l3-envoy-gateway-PASS.md` | `6c1444f` |
| **L3** | Modern north-south ingress via Envoy Gateway v1.9.1 (Gateway API v1) | `curl -H "Host: ..."` -> EnvoyProxy ClusterIP -> backend pod | `docs/evidence/local-platform/l3-envoy-gateway-PASS.md` | `6c1444f` |
| **L4** | Argo CD v3.5.3 non-HA control plane with ClusterIP isolation | `kubectl -n argocd get pods` (7/7 running, 0 restarts) | `docs/evidence/local-platform/l4-argocd-PASS.md` | `9e339ab` |
| **L5** | FlashSale distributed stateful stack (Postgres, Redis, RabbitMQ, EF Core) | `kubectl -n flashsale get pods,pvc` (All Ready, migration exit 0) | `docs/evidence/local-platform/l5-l6-flashsale-PASS.md` | `Current` |
| **L6** | Async order pipeline (JWT Auth -> 202 -> Completed -> Pay -> /orders/me) | Automated script running against `flashsale.local` via Envoy Gateway | `docs/evidence/local-platform/l5-l6-flashsale-PASS.md` | `Current` |
| **L7** | LegacyApp productionized Node.js service running on kind | `curl -H "Host: legacy.local" http://127.0.0.1:8088/health` (200 OK) | `docs/evidence/local-platform/l7-legacyapp-PASS.md` | `Current` |
| **L8** | Shared Gateway API multiplexing isolated application namespaces | Traffic routed to `flashsale.local` and `legacy.local`, 404 for unmatched | `docs/evidence/local-platform/l8-shared-gateway-PASS.md` | `6aec359` |
| **L9** | GitOps forward sync & Git-revert automated rollback via Argo CD | Upstream commit push -> OutOfSync -> Synced -> git revert -> Rollback | `docs/evidence/local-platform/l9-gitops-PASS.md` | `0ccb6f2` / `308e042` |
| **L10** | Prometheus metrics scraping across cluster, Argo CD, and Envoy Gateway | `curl http://127.0.0.1:9090/api/v1/targets` (25 targets active, all `up`) | `docs/evidence/local-platform/l10-observability-PASS.md` | `Current` |
| **L10** | Grafana dashboards for Platform, Argo CD GitOps, and Workloads | `curl http://admin:...@127.0.0.1:3000/api/search` (27 dashboards loaded) | `docs/evidence/local-platform/l10-observability-PASS.md` | `Current` |
| **L10** | Live alert fire-and-resolve cycle (`LocalPlatformMetricSourceDown`) | Simulated scraper outage -> firing (`15:33:25Z`) -> resolved (`15:35:17Z`) | `docs/evidence/local-platform/l10-observability-PASS.md` | `Current` |
| **L11** | Full interview demo script & automated test harness | `./scripts/demo-local-platform.sh` (100% green execution in <= 5 mins) | `docs/interview-demo/local-platform.md` | `Current` |

---

## Resource Footprint Audit (Measured)

- **Host Architecture**: Apple Silicon (`arm64`), 16 GiB RAM.
- **Docker VM Allocated Memory**: 7.75 GiB limit.
- **Measured Consumption**:
  - `local-platform-control-plane`: 1.89 GiB
  - `local-platform-worker`: 1.88 GiB
  - `local-platform-worker2`: 1.50 GiB
  - **Total Kind Footprint**: ≈ 5.27 GiB
  - **Remaining VM Headroom**: ≈ 2.48 GiB
- **Zero OOMKilled events**, zero evicted pods.

---

## Boundaries & Non-Claims

1. **No Azure cluster is currently running.** The AKS foundation was applied
   once on 2026-09-21 (see `evidence/phase7a/`) and then stopped and torn down.
   Nothing above is Azure evidence except what is explicitly labelled
   `AZURE_VALIDATION` — which, as of this writing, is the 7A foundation only.
   The cluster autoscaler, pod autoscaler, enforced NetworkPolicy, PDB and drain
   proofs have **never** been run on Azure.
2. **Local success is not Azure success.** Every kind row above is
   `PRE_AZURE_DRY_RUN`. It shows the manifests and the operating model work on
   the same Kubernetes minor line. It does not show that an AKS-managed control
   plane, a managed observability backend, or Azure CNI enforce them.
3. **No ELK on AKS.** ELK is `IMPLEMENTED_TESTED_LOCAL` and
   `NOT_APPLIED_ON_AKS_QUOTA` — the measured 10 vCPU regional ceiling cannot fit
   Elasticsearch alongside the rest of the observability stack. This is a
   capacity decision with numbers attached, not unfinished work.
4. **No SLO history exists.** No availability figure, latency percentile or error
   budget in this repository is backed by 30 days of production traffic.
   `PRODUCTION_30_DAY_HISTORY = NOT_AVAILABLE` until real history does.
5. **No Experimental Buzzwords**: No GraphQL, no Ollama/Qwen local inference in
   k8s, no Kafka/Saga, no Istio Ambient.
