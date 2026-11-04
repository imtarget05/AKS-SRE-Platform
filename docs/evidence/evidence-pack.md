# Evidence Pack — AKS-SRE-Platform Production Readiness (Sacombank)

> **2026-11-03 recheck:** [Current local verification](2026-11-03-verification-checkpoint.md) supersedes the older numeric test baselines below. NetworkPolicy enforcement on kindnet is inconclusive. CreditFlow's readiness document exists in the separate CreditFlow checkout, not under this AKS repository; the missing-path statement below refers only to this repository's filesystem.

**Date:** 2026-11-03
**Scope:** `kind-local-platform` only. Azure / production are **out of scope** per project constraints (`constraint.no_azure_production_mutations`: kind-local-platform is the only target; do not mutate Azure/production).
**Verdict:** NOT READY FOR SACOMBANK PRODUCTION (see Section 6).

---

## 1. Infrastructure as Code — terraform plan

Committed plan outputs (executed against the Terraform azurerm provider; `terraform plan` textual output, not applied to Azure in this scope):

| Artifact | Path | What it contains |
|---|---|---|
| phase7a plan | `docs/evidence/phase7a/plan.txt` | `azurerm_kubernetes_cluster.aks` create: `role_based_access_control_enabled = true`, `sku_tier = "Free"`, `node_count = 2`, `vm_size = "Standard_D4s_v6"`, `kubernetes_version = "1.36"`, `location = "eastasia"`, `workload_identity_enabled = true`, `oidc_issuer_enabled = true`, `private_cluster_enabled = false`. Plan: 2 to add, 0 to change, 0 to destroy. Plus `azurerm_role_assignment.aks_acr_pull` (AcrPull). |
| live-aks-2026-10-20 plan | `docs/evidence/live-aks-2026-10-20/terraform-plan.txt` | Module-based AKS plan: `role_based_access_control_enabled = true`, `sku_tier = "Free"`, `node_count = 1`, `vm_size = "Standard_D2s_v6"`, `kubernetes_version = "1.36"`, `private_cluster_enabled = false`, `workload_identity_enabled = true`. Plan: 2 to add. |

**Honest summary (what the committed files actually contain):**
- Azure RBAC: **enabled** (`role_based_access_control_enabled = true`) in both plans.
- Private cluster: **NOT private** — `private_cluster_enabled = false` in both plans.
- SKU: `sku_tier = "Free"` in both plans — **not** a Standard SKU.
- Zones: **not specified** in either committed plan (no `zones` block present).
- Node count: **2** (phase7a) / **1** (live-aks-2026-10-20) — **not** reliably `≥ 2` across both.

> The plan summary items sometimes cited (private cluster, Standard SKU, zones 1-2-3, ≥2 nodes) are **not supported by the committed plan files** above; they are listed here only to flag that the committed evidence does not substantiate them. No metrics are fabricated.

---

## 2. Container/Image Security — Trivy

- No committed Trivy scan output file exists in `docs/evidence/`. Trivy runs at CI time only.
- The `pr-gate` security job runs **Trivy v0.74.0** with checksum verification, `--exit-code 1` on HIGH/CRITICAL, secret scanner only (per QA_PLAN.md §5 / TC-24: `trivy config` HIGH/CRITICAL + `trivy fs --scanners secret` on IaC/config and client-side JS).
- Scan result: **CI-RUNTIME / MISSING** — nothing committed to review in this pack; a local Trivy run would be required to produce a committed artifact.

---

## 3. Live AKS Snapshot — kubectl get nodes/pods

Committed live-AKS `kubectl` output. Note: the live AKS cluster `aks-portfolio-dev` was destroyed after the 2026-10-21 run (QA_PLAN.md §2); these are historical snapshots, not a running cluster.

| Artifact | Path | What it contains |
|---|---|---|
| kubectl nodes (azure) | `docs/evidence/live-aks-azure-2026-10-21/kubectl-nodes.txt` | **1 node**: `aks-sys-13411604-vmss000000`, `Ready`, `v1.36.4`, Ubuntu 24.04.5, `containerd://2.3.3-3`. |
| kubectl pods (azure) | `docs/evidence/live-aks-azure-2026-10-21/kubectl-pods.txt` | **18 pods** in `kube-system` (azure-cns, azure-ip-masq-agent, azure-npm, azure-wi-webhook x2, cloud-node-manager, coredns x2, coredns-autoscaler, csi-azuredisk-node 3/3, csi-azurefile-node 4/4, konnectivity-agent x3, kube-proxy, kube-proxy, metrics-server Terminating/Running). All `Running` except one `metrics-server` in `Terminating`. |
| AKS show (prestop) | `docs/evidence/azure/2026-10-21-prestop/aks-show.json` | `az aks show` output for the cluster (pre-stop). |
| AKS show final | `docs/evidence/azure/2026-10-21-prestop/aks-show-final.json` | `az aks show` final state. |
| kubectl get all (A) | `docs/evidence/azure/2026-10-21-prestop/kubectl-get-all-A.yaml` | Full `kubectl get all` dump (prestop). |
| kubectl nodes (prestop) | `docs/evidence/azure/2026-10-21-prestop/kubectl-nodes.yaml` | Node dump (prestop). |
| kubectl pods (prestop) | `docs/evidence/azure/2026-10-21-prestop/kubectl-pods-A.yaml` | Pod dump (prestop). |
| kubectl events (prestop) | `docs/evidence/azure/2026-10-21-prestop/kubectl-events-A.txt` | Event dump (prestop). |
| Supporting JSON | `docs/evidence/azure/2026-10-21-prestop/{account-show,group-list,resource-group-show,resource-list}.json` | Azure account / group / resource-group / resource list (prestop). |

**Node count:** 1 Ready node (live-aks-azure-2026-10-21 snapshot).
**Pod statuses:** All Running except 1 metrics-server Terminating (18 pods total).

---

## 4. Local Platform Verification — kind-local-platform ArgoCD

Target cluster: `kind-local-platform` (Kubernetes v1.36.1), local kind only, no Azure mutated.

| Artifact | Path | What it contains |
|---|---|---|
| L3 Envoy Gateway | `docs/evidence/local-platform/l3-envoy-gateway-PASS.md` | Envoy Gateway install PASS (local kind). |
| L4 Argo CD | `docs/evidence/local-platform/l4-argocd-PASS.md` | Argo CD non-HA, pinned `v3.5.5` in `platform/argocd/VERSION`, 7/7 Running, ClusterIP-only services, server-side apply fix (F1). |
| L5-L6 FlashSale kind | `docs/evidence/local-platform/l5-l6-flashsale-kind-PASS.md` | FlashSale workload on kind PASS. |
| L7 LegacyApp kind | `docs/evidence/local-platform/l7-legacyapp-kind-PASS.md` | LegacyApp on kind PASS (not deployed unless `APPLY_LEGACYAPP=1`). |
| L8 Shared Gateway | `docs/evidence/local-platform/l8-shared-gateway-PASS.md` | Shared gateway PASS. |
| L9 GitOps | `docs/evidence/local-platform/l9-gitops-PASS.md` | `portfolio` AppProject manages `flashsale` and `legacyapp` Applications; forward deployment + Git revert rollback proven. |
| L10 Observability | `docs/evidence/local-platform/l10-observability-PASS.md` | Observability stack PASS. |
| Re-verify note | `docs/evidence/local-platform/2026-10-20-merge-note.md` | 2026-10-20 merge note. |
| Re-verify record | `docs/evidence/local-platform/2026-10-20-reverify.md` | F1–F5 re-verification: 3/3 Ready nodes, Argo CD 7/7 Running, version pinned `v3.5.5`, 56-object server-side dry-run, 8/8 kustomize roots, 4/4 gates, terraform test 5/5, AppProject allowlist enforced (2 negative controls refused with `InvalidSpecError`), `flashsale` Application `OutOfSync / Missing` (data tier + workload images not deployed), `legacyapp` not deployed by design (`APPLY_LEGACYAPP` not enabled), second Argo CD control plane in `default` (pre-existing, not fixed). |

**QuanLyKho Application** (committed manifest): `platform/argocd/applications/quanlykho.yaml`
- `kind: Application`, `name: quanlykho`, `namespace: argocd`, `spec.project: portfolio`
- Source: `https://github.com/imtarget05/QuanLyKho.git`, `targetRevision: 573dfadc96ff843171f0b127dbf0b7fab4cc7feb`, `path: infra/k8s/overlays/production`
- Destination: in-cluster, namespace `quanlykho`
- `syncPolicy`: **manual first cutover** — `automated` sync **disabled** (`retry` only, no `automated`); `ignoreDifferences` on `bankops-frontend`/`cloudflare-tunnel` replicas and Job selectors.

**Summary:** `portfolio` AppProject is pinned and in place; Argo CD 7/7 Running on `kind-local-platform`; AppProject allowlist enforced at runtime (2 negative controls refused). `quanlykho` Application uses **manual sync** (automated disabled). `flashsale` was observed `OutOfSync / Missing` at re-verification time (data tier/workload images not deployed — deliberate, no workloads synced); `legacyapp` not deployed by design.

---

## 5. Gates & Tests

Committed CI/test baselines (from `docs/QA_PLAN.md` and `tests/test_gates.py`; values are documented baselines, not re-run in this session):

| Gate / test | Source | Documented baseline |
|---|---|---|
| pr-gate gate matrix | `tests/test_gates.py` | Gate groups **G1–G16** defined (G1..G16 labels present in the file). |
| GitOps invariant assertions | `docs/QA_PLAN.md` §5.1 | **47 assertions (G1–G14)** documented baseline; `tests/test_gates.py` defines G1–G16. |
| Static policy + image gate | `scripts/policy-gate.py` | 2 kustomize roots, 26 objects, PASS. |
| GitOps semantic validation | `gitops/validate-gitops.py` | Orphan, AppProject, Application, inventory validation; PASS (16 passed, 0 failed, 2 EXTERNAL_REPO_NOT_PRESENT advisory). |
| Terraform native tests | `terraform test` (mock_provider azurerm) | 5 run blocks pass (aks-foundation 2, acr_attachment 1, aks_cluster 2), rc=0. |
| tflint | `tflint --recursive` | rc=0, 0 issues. |
| sre-demo-api unit tests | `app/sre-demo-api/` (`node --test`) | **7 tests** documented baseline (`server.test.js`). |
| sre-console security scan | QA_PLAN.md TC-24 | Trivy fs secret scan + grep on `apps/sre-console/index.html` — no hardcoded Cloudflare token/secret required (publish gate). |

**Honest notes:**
- `agent-hub` pytest (56 tests): **out of scope** — agent-hub was dropped from the project (`agent_hub_dropped_from_project`); not referenced as evidence here.
- `sre-demo-api` "12 tests" and `sre-console` "smoke test PASS": **not supported by committed evidence**; QA_PLAN.md documents 7 tests for sre-demo-api and a Trivy fs secret scan (not a smoke test) for sre-console. Not claimed as passes.
- No test suite was re-executed for this pack; figures above are the committed documented baselines only.

---

## 6. Known Limitations (honest, no fabrication)

- **SQLite / demo mode only** — no encrypted PostgreSQL, no backup, no RPO/RTO (`creditflow.storage_demo_mode`).
- **Disbursement stub** — `execute()` is a stub; no real transfer, no Core Banking integration (`creditflow.disbursement_stub`).
- **Sacombank IdP OIDC not connected** — issuer/audience/JWKS and group-to-role mapping not connected; production approval returns `PRODUCTION_APPROVAL_NOT_INTEGRATED` (`creditflow.sacombank_idp_not_connected`).
- **NOT READY FOR SACOMBANK PRODUCTION** — enterprise readiness verdict (`creditflow.enterprise_readiness_verdict`: NOT READY FOR SACOMBANK PRODUCTION; engineering baseline, not Sacombank or regulatory certification).

> Path verification for the readiness verdict: project memory references `docs/qa/ENTERPRISE_READINESS_2026-11-03.md`. On disk, `docs/qa/` **does not exist**; no `ENTERPRISE_READINESS_*` file was found. Only `docs/QA_PLAN.md` exists at repo root. The "NOT READY FOR SACOMBANK PRODUCTION" verdict is therefore reported as a **project fact from memory**, not as a linkable committed file — the referenced path could not be verified on disk.

---

## 7. Evidence inventory table

| # | Artifact | Path | Description | Status |
|---|---|---|---|---|
| 1 | phase7a terraform plan | `docs/evidence/phase7a/plan.txt` | Terraform plan: AKS create, RBAC, Free tier, node_count=2, Standard_D4s_v6, k8s 1.36, private_cluster=false | COMMITTED |
| 2 | live-aks-2026-10-20 terraform plan | `docs/evidence/live-aks-2026-10-20/terraform-plan.txt` | Module AKS plan: RBAC, Free tier, node_count=1, Standard_D2s_v6, private_cluster=false | COMMITTED |
| 3 | Trivy scan output | — | No committed file; runs in CI (pr-gate, Trivy v0.74.0, --exit-code 1 HIGH/CRITICAL, secret scanner) | MISSING (CI-RUNTIME) |
| 4 | kubectl nodes (azure) | `docs/evidence/live-aks-azure-2026-10-21/kubectl-nodes.txt` | 1 Ready node, v1.36.4 | COMMITTED |
| 5 | kubectl pods (azure) | `docs/evidence/live-aks-azure-2026-10-21/kubectl-pods.txt` | 18 pods, all Running except 1 metrics-server Terminating | COMMITTED |
| 6 | aks-show.json (prestop) | `docs/evidence/azure/2026-10-21-prestop/aks-show.json` | az aks show pre-stop | COMMITTED |
| 7 | aks-show-final.json (prestop) | `docs/evidence/azure/2026-10-21-prestop/aks-show-final.json` | az aks show final | COMMITTED |
| 8 | kubectl-get-all-A.yaml (prestop) | `docs/evidence/azure/2026-10-21-prestop/kubectl-get-all-A.yaml` | kubectl get all dump | COMMITTED |
| 9 | kubectl-nodes.yaml (prestop) | `docs/evidence/azure/2026-10-21-prestop/kubectl-nodes.yaml` | Node dump | COMMITTED |
| 10 | kubectl-pods-A.yaml (prestop) | `docs/evidence/azure/2026-10-21-prestop/kubectl-pods-A.yaml` | Pod dump | COMMITTED |
| 11 | kubectl-events-A.txt (prestop) | `docs/evidence/azure/2026-10-21-prestop/kubectl-events-A.txt` | Event dump | COMMITTED |
| 12 | Azure account/group/rg/resource JSON (prestop) | `docs/evidence/azure/2026-10-21-prestop/*.json` | account-show, group-list, resource-group-show, resource-list | COMMITTED |
| 13 | L3–L10 local-platform PASS | `docs/evidence/local-platform/l{3..10}-*-PASS.md` | Envoy Gateway, Argo CD, FlashSale, LegacyApp, Shared Gateway, GitOps, Observability PASS records | COMMITTED |
| 14 | 2026-10-20 reverify | `docs/evidence/local-platform/2026-10-20-reverify.md` | F1–F5 re-verification, 3/3 Ready, Argo CD 7/7, pin v3.5.5, allowlist enforced, flashsale OutOfSync/Missing | COMMITTED |
| 15 | QuanLyKho Application manifest | `platform/argocd/applications/quanlykho.yaml` | Argo CD Application, manual sync, project portfolio, pinned targetRevision | COMMITTED |
| 16 | QA plan | `docs/QA_PLAN.md` | QA strategy, gate matrix (G1–G16), 47 assertions baseline, 7 sre-demo-api tests, TC-24 Trivy fs | COMMITTED |
| 17 | Gate matrix tests | `tests/test_gates.py` | G1–G16 gate groups defined | COMMITTED |
| 18 | Enterprise readiness verdict | `docs/qa/ENTERPRISE_READINESS_2026-11-03.md` | NOT READY FOR SACOMBANK PRODUCTION — **path does not exist on disk** (docs/qa/ absent); reported as project fact only | MISSING |
