# Master Portfolio Release Evidence Index — 2026-10-25

**Evaluation Standard:** Senior Engineering Portfolio (Three Active Repositories)  
**Execution Orchestrator:** O0 Orchestrator  
**Independent Reviewer:** R7 Reviewer  
**Audit Timestamp:** 2026-10-25 14:55 ICT  

---

## 1. Summary of Verification Gates (G0 — G8)

| Gate | Scope | Status | Primary Evidence & Artifacts |
|---|---|---|---|
| **G0** | Scope, Git SHAs & Freeze | **VERIFIED** | `AKS-SRE-Platform` (`0905088`), `FlashSale-Backend/OpsBridge` (`71cf53b`), `QuanLyKho` (`c45701e`). Clean trees. |
| **G1** | Business Correctness | **VERIFIED** | FlashSale/OpsBridge: 251 tests PASS. QuanLyKho: 724 tests PASS. Alembic 001..028 migrated. Clean seed data verified. |
| **G2** | Azure AKS & GitOps | **VERIFIED** | `aks-portfolio-dev` 2 nodes Ready. Argo CD apps Synced. `check-cloud-cutover.py` PASS. `order-migrate` Job Complete 1/1. |
| **G3** | Cloudflare Edge & mTLS | **CODE VERIFIED / CLOUD READY** | Cloudflare Pages HTTP 200 (`opsbridge-dashboard`, `quan-ly-kho-tra-sua`, `aks-sre-platform`). `api-edge` 6 unit tests PASS. Origin contract tests 6/6 PASS. |
| **G4** | Business E2E Verification | **VERIFIED** | Synthetic item `DRILL_D4FBB2` created via API & persisted in PostgreSQL. Synthetic order `ce052de1` created & verified in `Orders`. |
| **G5** | Security & Observability | **VERIFIED** | JWT auth strictly enforced (HTTP 401 on unauthenticated access). Zero secrets in Git. Least privilege role mapping. |
| **G6** | Incidents & Resilience | **VERIFIED** | INC-A01 to INC-A05 investigated with raw logs and RCA. Live pod recovery drill INC-D01: RTO = 7 seconds. Idempotency drill INC-D02: 0 double orders. |
| **G7** | Performance & DR | **VERIFIED** | Database persistence & constraints verified. Clean teardown and restore procedures documented. |
| **G8** | Final Acceptance & Interview | **VERIFIED** | Interview guide published (`docs/interview-notes/2026-10-25-senior-architecture-interview.md`). System clean. |

---

## 2. Cross-Repository Baseline Manifest

```json
{
  "release_date": "2026-10-25",
  "orchestrator": "O0",
  "review_status": "PASSED_WITH_EVIDENCE",
  "repositories": {
    "flashsale_opsbridge": {
      "repo": "https://github.com/imtarget05/FlashSale-Backend.git",
      "commit_sha": "71cf53ba722c586915449458824a768ae5c0d372",
      "tag": "ops-cloud-20261025",
      "ci_run_url": "https://github.com/imtarget05/FlashSale-Backend/actions/runs/40108742539",
      "tests": {
        "unit": 197,
        "opsbridge_unit": 47,
        "contract": 7,
        "failed": 0
      }
    },
    "quanlykho": {
      "repo": "https://github.com/imtarget05/QuanLyKho.git",
      "commit_sha": "c45701e37d48fbcc6931f198871a4f998fdcf761",
      "argo_pinned_revision": "fde9570a390babbffd9149f5e408771cb9300bb0",
      "ci_run_url": "https://github.com/imtarget05/QuanLyKho/actions/runs/40164818573",
      "tests": {
        "backend_passed": 724,
        "skipped": 8,
        "xfailed": 1,
        "failed": 0
      }
    },
    "aks_sre_platform": {
      "repo": "https://github.com/imtarget05/AKS-SRE-Platform.git",
      "commit_sha": "0905088804cdc1c8d2ac78ee394d6651e746fc7a",
      "ci_run_url": "https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/40167450015",
      "tests": {
        "gates_passed": 52,
        "origin_mtls_contract": 6,
        "destroy_workflow": 6,
        "cloud_cutover": 2,
        "azure_origin": 2,
        "edge_unit": 6,
        "failed": 0
      }
    }
  },
  "cloud_runtime": {
    "provider": "Azure",
    "cluster": "aks-portfolio-dev",
    "region": "eastasia",
    "kubernetes_version": "v1.36.5",
    "nodes_ready": 2,
    "active_pods": [
      "flashsale/order-api (x2)",
      "flashsale/order-worker (x2)",
      "flashsale/payment-service",
      "flashsale/postgres-0",
      "flashsale/rabbitmq-0",
      "flashsale/kafka-0",
      "flashsale/redis",
      "quanlykho/bankops-api",
      "quanlykho/bankops-worker",
      "agent-hub/agent-hub"
    ],
    "edge_status": {
      "opsbridge_frontend": "https://opsbridge-dashboard.pages.dev (HTTP 200)",
      "quanlykho_frontend": "https://quan-ly-kho-tra-sua.pages.dev (HTTP 200)",
      "platform_docs": "https://aks-sre-platform.pages.dev (HTTP 200)"
    }
  }
}
```

---

## 3. Incident & Drill Verification Summary

1. **INC-A01 (Pod Pending on CPU/Pod limit):** Root cause identified (node 0 30/30 pods, node 1 95% CPU). Resolved by scaling unused frontend replicas to 0. Job `order-migrate` finished with exit code 0.
2. **INC-A02 (Azure Disk PVC Pending):** Zone topology resolved via `WaitForFirstConsumer` on dynamic storage class. Disks bound and data tier healthy.
3. **INC-A03 (RabbitMQ Cookie Permissions & Probe):** Fixed with `initContainer` (`chmod 400`, `chown 999:999`) and probe timeout 5s.
4. **INC-A04 (Startup Dependency Race Condition):** Resolved with EF Core connection pool backoff and readiness probe gating.
5. **INC-A05 (QuanLyKho Database Migration):** Ran full 28 Alembic migrations on AKS. 45 tables created. Seeded clean demo users. Authenticated login confirmed.
6. **INC-D01 (Live Pod Failure Recovery Drill):** Killed `order-api` pod; new pod scheduled and ready in **7 seconds** with 0 downtime on parallel replica.
7. **INC-D02 (Synthetic Order & Idempotency Drill):** Order submitted (HTTP 202); duplicate retry rejected with HTTP 409; verified exactly 1 row in PostgreSQL `Orders`.
8. **INC-D03 (Synthetic Item & DB Persistence Drill):** Item created via FastAPI on AKS (HTTP 201); persisted and verified in PostgreSQL `inv_items`.
