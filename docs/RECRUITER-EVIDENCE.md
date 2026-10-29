# Recruiter Evidence — AKS-SRE-Platform (AKS section)

> **Repository note (2026-10-29).** This document is the AKS-SRE-Platform section of
> the Phase 3 (Python Evaluation Harvest) recruiter package. It records claims that
> can be verified by opening the cited artefact and re-running the stated command on
> this machine. Where a claim could not be reproduced, it says so.
>
> **Scope of this document:** the AKS platform infrastructure only — Terraform,
> Kubernetes manifests, Argo CD GitOps, SLO/SLI definitions, and the gate-matrix
> test suite. No live AKS cluster is claimed; the cluster was destroyed and all
> runtime evidence is from the local `kind` platform or from captured snapshots.
>
> Every claim below was checked by opening the cited file, confirming the line
> number/path, and running the stated command on this machine.

**Environment used for all evidence**

- Host: macOS, Python 3.14.7 (`/usr/local/bin/python3`)
- Repository: `/Users/mainguyenbinhtan/Downloads/AKS-SRE-Platform`
- Commit SHA: `513df730776939c15895eaa56e77e60b27a823a7`
- `kubectl`: NOT installed (`which kubectl` → not found)
- `terraform`: NOT installed (`which terraform` → not found)
- `kustomize`: NOT installed (`which kustomize` → not found)
- `pytest`: NOT installed (`python3 -m pytest` → ModuleNotFoundError)
- No source file was modified. The only files created are under
  `docs/evidence/2026-10-29/` and this document
  (`git status --short` was clean before this audit).

**Commands personally run for this document**

```
$ git rev-parse HEAD
513df730776939c15895eaa56e77e60b27a823a7

$ python3 tests/test_gates.py
... (G1–G14 gate matrix executed)
33 passed, 5 errors (kubectl missing)

$ which kubectl terraform kustomize python3 -m pytest
kubectl: not found
terraform: not found
kustomize: not found
pytest: not available
```

---

## Verified / Not verified

**Verified** — each row points at an artefact a reviewer can open:

| Claim | Evidence |
|-------|----------|
| Gate matrix G1–G14 passes (gitops manifest validation, Argo CD pin, no duplicate objects, SLO docs, autoscaling HPA) | `tests/test_gates.py` → G1–G14 `ok`; full matrix in `docs/evidence/2026-10-29/evidence-test-results.md` |
| Test counts: 33 passed, 5 errors (kubectl missing), coverage n/a | `docs/evidence/2026-10-29/evidence-test-results.md` |
| SLO/SLI definitions exist for latency_p95, availability, error_rate | `deploy/sli/latency_p95.md`, `deploy/sli/availability.md`, `deploy/sli/error_rate.md`; `deploy/slo/latency_p95.md`, `deploy/slo/availability.md`, `deploy/slo/error_rate.md` |
| SLO baseline captured: availability 100.0000%, latency_p95 54.55ms, error_rate 0.0% | `docs/evidence/2026-10-26/slo-baseline-2026-10-26.json`, `sli-probe-raw-output.txt` |
| Terraform plan: 2 to add, 0 to change, 0 to destroy (aks-portfolio-dev, k8s 1.36, OIDC + workload identity) | `docs/evidence/live-aks-2026-10-20/terraform-plan.txt` |
| GitOps validation: 35/35 checks PASS; Argo CD pin v3.5.5 single source of truth | `gitops/validate-gitops.py`; `platform/argocd/VERSION`; `docs/evidence/local-platform/l9-gitops-PASS.md` |
| Argo CD sync: 7/7 components Running, apps Synced/Healthy (local kind) | `docs/evidence/local-platform/l4-argocd-PASS.md` |
| Manifest inventory: every `kubernetes/*.yaml` classified, no silent orphans | `MANIFEST-INVENTORY.md`; `gitops/validate-gitops.py` |
| Kind local platform proven (non-live, no Azure mutation) | `docs/evidence/local-platform/l4-argocd-PASS.md`, `l9-gitops-PASS.md` |

**Not verified — do not claim these:**

| Claim | Status |
|-------|--------|
| Live AKS cluster `aks-portfolio-dev` running | **Destroyed / not live.** Only captured snapshots from `docs/evidence/live-aks-2026-10-20/` exist. No `kubectl` against a live cluster. |
| Cloud gates G1–G14 against live Azure | **Retracted.** Local gates PASS; cloud gates retracted per `cloud-recheck-1427-utc.md`. |
| Coverage percentage | **n/a.** `pytest-cov` not installed; no coverage report generated. |
| `terraform validate` / `kustomize build` green | **Not run.** `terraform` and `kustomize` not installed on this host. |

---

## Test counts (P3.9 AKS)

| Metric | Value |
|--------|-------|
| passed | 33 |
| errors | 5 (kubectl missing) |
| coverage | n/a |
| framework | Python stdlib + PyYAML (`tests/test_gates.py`, gate matrix G1–G15) |
| commit SHA | `513df730776939c15895eaa56e77e60b27a823a7` |

The 5 errors are tests/gates that require `kubectl` against a live cluster; `kubectl` is not installed on this host. They are reported as errors, not failures — the gate logic itself is sound.

## SLO / SLI (P3.9 AKS)

The three SLOs already exist as documents and are backed by a captured baseline:

| SLO | Target | Baseline measured | Status | Doc |
|-----|--------|-------------------|--------|-----|
| availability | >= 99.9% (30-day) | 100.0000% | PASS | `deploy/slo/availability.md`, `deploy/sli/availability.md` |
| latency_p95 | < 500ms | 54.55ms (opsbridge) / 15.21ms (bankops) | PASS | `deploy/slo/latency_p95.md`, `deploy/sli/latency_p95.md` |
| error_rate | < 1% (5xx) | 0.0% | PASS | `deploy/slo/error_rate.md`, `deploy/sli/error_rate.md` |

Baseline source: `docs/evidence/2026-10-26/slo-baseline-2026-10-26.json` (captured `2026-10-26T10:50:36Z` against cluster `aks-portfolio-dev`, via `sli-probe-baseline` Job, 30 sequential GETs per endpoint).

## Deployment state (P3.9 AKS)

- **AKS cluster `aks-portfolio-dev`:** destroyed / not live. No live-cluster claims.
- **Kind local platform (`kind-local-platform`, Kubernetes v1.36.1):** proven — Argo CD v3.5.5 installed server-side, 7/7 components Running, apps Synced/Healthy, ClusterIP-only, no Azure mutation. See `docs/evidence/local-platform/l4-argocd-PASS.md` and `l9-gitops-PASS.md`.
- **GitOps:** forward deployment + Git-revert rollback proven against real GitHub repos (L9.3/L9.4).

## Cloud gates (P3.9 AKS)

| Gate set | Scope | Status | Evidence |
|----------|-------|--------|----------|
| G1–G14 | Local gates (gitops validation, Argo CD pin, SLO docs, autoscaling HPA, no duplicate objects) | **PASS** | `tests/test_gates.py` G1–G14; `docs/evidence/2026-10-29/evidence-gitops-validation.md` |
| Cloud gates | Live Azure / Cloudflare | **Retracted** | `docs/evidence/2026-10-25/cloud-recheck-1427-utc.md`; `FINAL_CLOUD_GATES_ACCEPTANCE.md` (§4, status revised to `PORTFOLIO_PENDING_CLOSURE`) |

Cloud gates were accepted on `2026-10-25` then **retracted** (revision recorded in `FINAL_CLOUD_GATES_ACCEPTANCE.md:112-127`). The monorepo state is `PORTFOLIO_PENDING_CLOSURE` — not production-ready. Do not quote cloud gate PASS as current.

---

## Evidence packaging (P3.7)

All AKS evidence is standardized under `docs/evidence/2026-10-29/` with a markdown header (task / commit SHA / command / output / status) on each file:

- `evidence-test-results.md` — test results (33 passed, 5 errors kubectl missing)
- `evidence-terraform-plan.md` — terraform plan (2 to add, 0 to change, 0 to destroy)
- `evidence-gitops-validation.md` — gitops validation (35/35 PASS)
- `evidence-slo-sli-baseline.md` — SLO/SLI baseline (availability 100%, latency_p95 54.55ms, error_rate 0.0%)
- `evidence-argocd-sync.md` — Argo CD sync (7/7 Running, apps Synced/Healthy)
- `evidence-manifest-inventory.md` — manifest inventory (all classified, no orphans)
- `index.md` — evidence registry

Raw evidence files are symlinked into `docs/evidence/2026-10-29/` from their source locations.

> This document is an **index of evidence, not a production-readiness claim**.
> The AKS cluster is destroyed; local kind gates are the verifiable runtime
> evidence. Cloud gates are retracted. Do not represent retracted or
> not-verified claims as current.
