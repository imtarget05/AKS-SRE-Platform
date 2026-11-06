# T14 — Production Go/No-Go Rehearsal Criteria

**Task:** T14 — Production go/no-go rehearsal criteria (documentation only)
**Branch:** `codex/wave3-t12-t14`
**SHA (AKS-SRE-Platform):** `f064ad3`
**Date:** 2026-11-06
**Status:** BLOCKED — pending Azure live evidence (G09–G12) and named go/no-go owner

---

## 1. Go/No-Go Criteria

A production go-live decision requires ALL of the following:

| Criterion | Requirement |
|---|---|
| All P0 gates PASS | Every P0-priority gate (G01–G12 where P0) must have PASS status with raw evidence |
| No open P0 residual risk | All P0 risks must be disposed (accept/mitigate/transfer with owner sign-off) |
| Cost cap approved | Monthly cost estimate reviewed and capped by account owner (H0) |
| Rollback tested and documented | Rollback procedure executed with measured RTO/RPO |
| Named go/no-go owners | Release owner, security owner, system owner each sign off |
| Azure live evidence | G09–G12 (Azure runtime gates) verified on a live cluster |

A **no-go** is triggered if any P0 gate is OPEN/FAIL, any P0 risk is undisposed, or any required owner declines to sign.

---

## 2. Gate Status Table (G01–G12)

Gate definitions are based on the gate matrix in `tests/test_gates.py` (G1–G16 group) and the gate references across `docs/`, `tasks/`, and `plans/`. Mapping: G01–G12 corresponds to G1–G12 in the repository's gate numbering.

| Gate | Title | Required env | Current status | Evidence available | Evidence still needed |
|---|---|---|---|---|---|
| G01 | Repository consistency & formatting | LOCAL | PASS | Ruff passes, `terraform fmt -check -recursive` clean, 5 TF test roots pass (16 runs) | None |
| G02 | Terraform validate/test | LOCAL | PASS | All 5 roots valid; `terraform test` 5 run blocks across 3 roots, all passing | None |
| G03 | tflint recursive | LOCAL | PASS | tflint 0 issues across all 10 directories, pinned AzureRM plugin | None |
| G04 | Kustomize render | LOCAL | PASS | All maintained Kustomize roots render and schema-check | None |
| G05 | Kubeconform | LOCAL | PASS | kubeconform -strict: valid objects, 0 invalid, 0 errors | None |
| G06 | Manifest inventory | LOCAL | PASS | MANIFEST-INVENTORY.md classifies every manifest; unclassified YAML fails CI | None |
| G07 | Static policy gate | LOCAL | PASS | Policy gate PASS: 2 kustomize roots, 26 objects; `:latest` rejected | None |
| G08 | GitOps external validation | LOCAL | PASS | 42 PASS, 0 FAIL, 0 NOT_PRESENT with repo-map | 2 `EXTERNAL_REPO_NOT_PRESENT` (advisory, not blocking) |
| G09 | Argo CD version pin | LOCAL | PASS | `platform/argocd/VERSION = v3.5.5`, single source of truth, installer asserts | None |
| G10 | Duplicate AppProject prevention | LOCAL | PASS | Duplicate AppProject deleted; validator fails on duplicate names | None |
| G11 | AKS runtime / cluster apply | AZURE_VALIDATION | BLOCKED | Historical Phase 7A PASS (2026-09-21); cluster destroyed since | Live cluster apply, workload sync, node/pod verification |
| G12 | Azure runtime / cost / state | AZURE_VALIDATION | BLOCKED | No current cluster; cost unknown; state backend orphaned (switched to `local`) | Live Azure inventory, cost export, state backend decision |

**Legend:** LOCAL = can be verified without Azure; AZURE_VALIDATION = requires live Azure cluster.

### Gates G01–G10: PASS (LOCAL)

All ten local gates are green. Evidence: CI runs, raw output files, `tests/test_gates.py` (56/56 assertions), PR gate workflow results.

### Gates G11–G12: BLOCKED (AZURE_VALIDATION)

Both require a live AKS cluster. The cluster was destroyed 2026-10-21 and again 2026-11-05. No `az login`, no `terraform apply`, no cluster exists today.

---

## 3. Residual Risks and Disposition

| Risk ID | Description | Likelihood | Impact | Disposition | Owner |
|---|---|---|---|---|---|
| R1 | No live AKS cluster; G11/G12 cannot be verified | High | High | **Mitigate** — provision transient cluster, apply gates, destroy after evidence (Cost Safety Mode) | Platform owner (P03) |
| R2 | Orphaned terraform state backend (`azurerm` → `local` switch, commit `d628250`) | Medium | High | **Mitigate** — restore remote backend or document as abandoned | Platform owner (P03) |
| R3 | Current Azure cost unknown; cluster may be running with unattributed spend | Medium | Medium | **Accept** — read-only inventory needed before any apply; budget alert as soft ceiling | Account owner (H0) |
| R4 | No secrets in Key Vault; JWT signing key, DB creds, RabbitMQ creds not provisioned | High | High | **Mitigate** — provision secrets outside Git before any deploy | Security owner |
| R5 | NetworkPolicy enforcement inconclusive on kindnet; no observed deny on AKS | Medium | Medium | **Accept** for validation; **Mitigate** before production (Cilium or AKS `azure` policy) | Platform owner (P03) |
| R6 | Second Argo CD install in `default` namespace (pre-existing, not fixed) | Low | Medium | **Accept** — documented known inconsistency; no cluster mutation planned | Platform owner (P03) |
| R7 | No go/no-go owner named | High | High | **Mitigate** — name release owner, security owner, system owner before go decision | Account owner (H0) |

Disposition legend: **Accept** = acknowledge and proceed; **Mitigate** = reduce before go; **Transfer** = shift to another party (none currently).

---

## 4. Required Sign-Offs

| Role | Responsibility | Status | Name | Date |
|---|---|---|---|---|
| Release owner | Overall go/no-go decision; owns release manifest, SHA/digest/revision | **UNASSIGNED** | — | — |
| Security owner | Secrets, JWT signing key, DB/RabbitMQ credentials, Key Vault/GitHub Secrets | **UNASSIGNED** | — | — |
| System owner | AKS cluster, ACR, terraform state, cost cap, infrastructure acceptance | **UNASSIGNED** | — | — |
| Account owner (H0) | Azure subscription, budget/cost cap approval, quota | **UNASSIGNED** | — | — |

No sign-off has been recorded. T14 is BLOCKED pending named owners.

---

## 5. Go/No-Go Decision Record

| Field | Value |
|---|---|
| Decision | **NO-GO (BLOCKED)** — cannot proceed without Azure live evidence and named owners |
| Reason | G11–G12 require live AKS cluster; cluster destroyed; no Azure credentials available; no go/no-go owners named |
| Blocking gates | G11 (AKS runtime), G12 (Azure runtime/cost/state) |
| Blocking risks | R1 (no cluster), R4 (no secrets), R7 (no owners) |
| Unblock requires | Azure subscription + budget + deploy rights; live cluster; secrets provisioned; three named owners |
| Re-evaluation trigger | User provides Azure credentials, cluster is provisioned, owners are named |

---

## 6. Constraints honored

- No `terraform apply` or `terraform destroy` was run.
- No Azure API calls were made.
- No Azure resources were created.
- No secrets were committed to the repository.
- This document is documentation only; no claim of Azure verification is made.

---

## What the user needs to provide to unblock T14

| Item | Who provides |
|---|---|
| Azure subscription ID + budget/cost cap approval | H0 (account owner) |
| Azure deploy rights (service principal / OIDC federation) | H0 + CI owner |
| Live AKS cluster with applied gates | Platform owner (P03) |
| Named release owner | User / account owner |
| Named security owner | User / account owner |
| Named system owner | User / account owner |
| Secrets: JWT_SIGNING_KEY, DB credentials, RabbitMQ credentials (Key Vault / GitHub Secrets) | Security owner |

T14 remains **BLOCKED** pending Azure live evidence (G09–G12) and named go/no-go owners.
