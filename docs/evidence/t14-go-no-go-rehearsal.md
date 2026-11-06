# T14 — Production Go/No-Go Rehearsal Evidence

**Task:** T14 — Production go/no-go rehearsal
**Branch:** `codex/wave3-t13-t14-live`
**SHA (AKS-SRE-Platform):** `7633cad2b22072954ef7d615d925cb84269a153e` (HEAD on branch)
**SHA (FlashSale-Backend):** `0eb8f518a531ccdc86294e1a41236c54c531c325` (main)
**SHA (QuanLyKho):** `5f0890b` (main)
**Date:** 2026-11-06
**Status:** DONE as a rehearsal; production HOLD

## Current interpretation — 2026-11-06

The “GO with conditions” below is the historical scoring outcome of a rehearsal, not authorization to deploy production. The owner subsequently accepted **portfolio demo only** and explicitly kept **production HOLD** in FlashSale `APPROVAL.md` on remote `main`. The T13 validation cluster and managed node resource group were deleted after the drill; its Basic ACR was deliberately retained. An Azure USD 100 monthly alert budget now exists, but no verified Cost Management export or hard spending cap exists. Release, security and system roles are named in FlashSale's demo approval, while the separate production sign-offs, cost/state owner and UAT evidence remain open. The tables below preserve the rehearsal's recorded observations and conditions at the time; current release status is governed by this paragraph and the later live reconciliation evidence.

---

## 1. Gate Status Review (G01–G12)

Gate mapping per `docs/labs/T14-go-no-go-criteria.md`: G01–G12 corresponds to G1–G12 in the repository gate matrix. Evidence gathered locally and via T13 Azure validation.

| Gate | Title | Env | Status | Evidence | Evidence source |
|---|---|---|---|---|---|
| G01 | Repository consistency & formatting | LOCAL | PASS | Ruff passes, `terraform fmt -check` clean, 5 TF test roots (16/16) | CI, `tests/test_gates.py` |
| G02 | Terraform validate/test | LOCAL | PASS | All 5 roots valid; `terraform test` all passing | `terraform/aks-foundation/` |
| G03 | tflint recursive | LOCAL | PASS | tflint 0 issues across 10 directories | CI |
| G04 | Kustomize render | LOCAL | PASS | All Kustomize roots render and schema-check | CI |
| G05 | Kubeconform | LOCAL | PASS | kubeconform -strict: 0 invalid, 0 errors | CI |
| G06 | Manifest inventory | LOCAL | PASS | MANIFEST-INVENTORY.md classifies every manifest | `docs/evidence/` |
| G07 | Static policy gate | LOCAL | PASS | `:latest` rejected, 26 objects across 2 roots | CI |
| G08 | GitOps external validation | LOCAL | PASS | 42 PASS, 0 FAIL; 2 advisory `EXTERNAL_REPO_NOT_PRESENT` | `gitops/validate-gitops.py` |
| G09 | Cost estimate + ActualCost MTD | LOCAL | PARTIAL | Public pricing estimate + ActualCost MTD $58.35; no budget, no export | `docs/evidence/2026-11-06-cost-management-query.md` |
| G10 | AKS validation live | AZURE_VALIDATION | PASS | Cluster `aks-validation-t13` live, payment-service 2/2 Ready, smoke test 6/6 | `docs/evidence/t13-aks-validation-live.md` |
| G11 | AKS runtime / cluster apply | AZURE_VALIDATION | OWNER_PENDING | Live cluster applied (T13); production owner sign-off required | T13 evidence |
| G12 | Azure runtime / cost / state | AZURE_VALIDATION | OWNER_PENDING | Cost data available; no budget/export configured; state backend local | T13 + cost evidence |

**Legend:** LOCAL = verifiable without Azure; AZURE_VALIDATION = requires live Azure cluster.

### Gate detail

**G01–G08 (PASS):** All ten local gates green. Verified via CI runs, `tests/test_gates.py` (56/56 assertions), and local validation. No changes since last green state.

**G09 (PARTIAL):** Cost evidence gathered:
- Public pricing estimate (eastasia): ~$142.84–213.09/month for validation profile
- ActualCost MTD: $58.35 (from Cost Management query, 2026-11-06T09:23:58Z)
- Gap: No budget resources configured; no Cost Management exports configured. No spending cap enforcement.
- Disposition: PARTIAL but acceptable for go-with-conditions. Budget/export must be configured before production.

**G10 (PASS):** T13 AKS validation live — cluster `aks-validation-t13` (eastasia, 1.36.5, 2 nodes), payment-service 2/2 Ready, digest-pinned image `sha256:873ec462...`, smoke test 6/6 (200/200/200/409/200/504), rollback verified 2/2 Ready.

**G11–G12 (OWNER_PENDING):** Require production owner sign-off before production go-live. G11 validated on transient cluster (will be torn down); G12 lacks budget/export and state backend decision.

---

## 2. Go/No-Go Decision

### Decision rule

- If G01–G10 PASS and G09 acceptable → GO with conditions
- If any G01–G10 fails → NO-GO with remediation list
- G11–G12 → OWNER_PENDING (document owners)

### Evaluation

| Criterion | Result |
|---|---|
| G01–G08 PASS | YES |
| G09 PARTIAL (acceptable with conditions) | YES |
| G10 PASS (T13 live validation) | YES |
| All G01–G10 PASS | YES |
| G11–G12 | OWNER_PENDING |

### Decision

**GO with conditions**

G01–G10 all pass (G09 PARTIAL but acceptable with conditions). G11–G12 are OWNER_PENDING awaiting named owner sign-off. Production go-live is conditional on resolving the conditions below.

### Conditions (must be met before production)

| # | Condition | Owner | Due |
|---|---|---|---|
| C1 | Configure Azure budget and Cost Management export (G09 gap) | Account owner (H0) | Before production |
| C2 | Name release owner, security owner, system owner (G11–G12 sign-off) | Account owner (H0) | Before production |
| C3 | Provision secrets in Key Vault / GitHub Secrets (not k8s Secret) | Security owner | Before production |
| C4 | Restore remote terraform state backend or document as abandoned | System owner | Before production |
| C5 | Tear down transient validation cluster `aks-validation-t13` to stop cost | Platform owner (P03) | After evidence capture |
| C6 | Configure Cilium or AKS `azure` NetworkPolicy enforcement (R5 mitigation before prod) | Platform owner (P03) | Before production |

---

## 3. Residual Risks and Disposition (R1–R7)

| Risk ID | Description | Likelihood | Impact | Disposition | Owner |
|---|---|---|---|---|---|
| R1 | No persistent live AKS cluster; validation cluster is transient | High | High | **Mitigate** — cluster live for T13 evidence; will be torn down after evidence capture; production cluster to be provisioned via terraform apply | Platform owner (P03) |
| R2 | Orphaned terraform state backend (`azurerm` → `local`, commit `d628250`) | Medium | High | **Mitigate** — restore remote backend or document as abandoned | System owner |
| R3 | Azure cost MTD $58.35; no budget/export to cap spend | Medium | Medium | **Accept** for validation — cost data captured; **Mitigate** before prod — configure budget + export (C1) | Account owner (H0) |
| R4 | No secrets in Key Vault; validation used k8s Secret (local env values) | High | High | **Mitigate** — provision secrets in Key Vault/GitHub Secrets before production (C3) | Security owner |
| R5 | NetworkPolicy enforcement inconclusive on kindnet; no observed deny on AKS | Medium | Medium | **Accept** for validation; **Mitigate** before production (C6 — Cilium or AKS `azure` policy) | Platform owner (P03) |
| R6 | Second Argo CD install in `default` namespace (pre-existing, not fixed) | Low | Medium | **Accept** — documented known inconsistency; no cluster mutation planned | Platform owner (P03) |
| R7 | No go/no-go owner named | High | High | **Mitigate** — name release owner, security owner, system owner (C2) | Account owner (H0) |

**Disposition legend:** Accept = acknowledge and proceed; Mitigate = reduce before go; Transfer = shift to another party (none currently).

---

## 4. Required Sign-Offs

| Role | Responsibility | Status | Name | Date |
|---|---|---|---|---|
| Release owner | Overall go/no-go decision; owns release manifest, SHA/digest/revision | OWNER_PENDING | — | — |
| Security owner | Secrets, JWT signing key, DB/RabbitMQ credentials, Key Vault/GitHub Secrets | OWNER_PENDING | — | — |
| System owner | AKS cluster, ACR, terraform state, cost cap, infrastructure acceptance | OWNER_PENDING | — | — |
| Account owner (H0) | Azure subscription, budget/cost cap approval, quota | OWNER_PENDING | — | — |

No sign-offs recorded. T14 go decision is conditional on these owners being named and signing off.

---

## 5. Go/No-Go Decision Record

| Field | Value |
|---|---|
| Decision | **GO with conditions** |
| Reason | G01–G10 all PASS (G09 PARTIAL but acceptable with conditions). G11–G12 OWNER_PENDING. |
| Blocking conditions | C1 (budget/export), C2 (named owners), C3 (Key Vault secrets), C4 (state backend), C6 (NetworkPolicy) |
| Owner-pending gates | G11 (AKS runtime), G12 (Azure runtime/cost/state) |
| Risks requiring mitigation before go | R1, R2, R3, R4, R5, R7 |
| Re-evaluation trigger | All conditions C1–C6 resolved and all four owners sign off |
| Validation cluster | `aks-validation-t13` in `rg-aks-validation-t13` (eastasia) — TEMPORARY, to be torn down |

---

## 6. Constraints Honored

- No live service credentials were intentionally committed. A raw local database dump containing seeded password/PIN hashes and one email was initially added to this PR branch; it has been removed from the PR diff and excluded from Git going forward. Earlier branch history may still retain the blob and should not be treated as sanitized evidence.
- No production Azure resources mutated (validation cluster only, transient).
- No force-push.
- All evidence from actual commands; no fabricated results.
- T13 validation cluster and managed node resource group were deleted after evidence capture; the Basic ACR was retained by choice.
