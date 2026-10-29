# Evidence Registry — AKS-SRE-Platform (P3.7)

**Date:** 2026-10-29  
**Commit SHA:** 513df730776939c15895eaa56e77e60b27a823a7  
**Purpose:** Standardized evidence package for AKS-SRE-Platform Phase 3 (Python Evaluation Harvest). Every claim "verified" has a backing file here.

## DoD

- [x] `docs/evidence/2026-10-29/` created
- [x] Each evidence file has a markdown header: task / commit SHA / command / output / status
- [x] Evidence registry (this file) available
- [x] Every claim "verified" has a backing file

## Evidence index

| # | Evidence | File | Task | Commit SHA | Status |
|---|----------|------|------|------------|--------|
| 1 | Test results | `evidence-test-results.md` | P3.7 (test results) | 513df730...23a7 | PASS (degraded: kubectl missing) |
| 2 | Terraform plan | `evidence-terraform-plan.md` | P3.7 (terraform plan) | 513df730...23a7 | PASS |
| 3 | GitOps validation | `evidence-gitops-validation.md` | P3.7 (gitops validation) | 513df730...23a7 | PASS |
| 4 | SLO/SLI baseline | `evidence-slo-sli-baseline.md` | P3.7 (SLO/SLI baseline) | 513df730...23a7 | PASS |
| 5 | Argo CD sync | `evidence-argocd-sync.md` | P3.7 (Argo CD sync) | 513df730...23a7 | PASS |
| 6 | Manifest inventory | `evidence-manifest-inventory.md` | P3.7 (manifest inventory) | 513df730...23a7 | PASS |

## Raw evidence files (symlinked into this directory)

| File | Source |
|------|--------|
| `test-gates-source.py` | `tests/test_gates.py` |
| `terraform-plan.txt` | `docs/evidence/live-aks-2026-10-20/terraform-plan.txt` |
| `slo-baseline-2026-10-26.json` | `docs/evidence/2026-10-26/slo-baseline-2026-10-26.json` |
| `sli-probe-raw-output.txt` | `docs/evidence/2026-10-26/sli-probe-raw-output.txt` |
| `slo-baseline-README.md` | `docs/evidence/2026-10-26/slo-baseline-README.md` |
| `argocd-l4-PASS.md` | `docs/evidence/local-platform/l4-argocd-PASS.md` |
| `gitops-l9-PASS.md` | `docs/evidence/local-platform/l9-gitops-PASS.md` |
| `argocd-applications.txt` | `docs/evidence/local-platform/2026-10-21-recreate/argocd-applications.txt` |
| `selfheal-application-syncpolicy.txt` | `docs/evidence/local-platform/2026-10-21-recreate/selfheal-application-syncpolicy.txt` |
| `manifest-inventory.md` | `MANIFEST-INVENTORY.md` |
| `cloud-recheck-1427-utc.md` | `docs/evidence/2026-10-25/cloud-recheck-1427-utc.md` |

## Related (P3.9)

- `RECRUITER-EVIDENCE.md` — recruiter package with test counts, SLO, deployment state, cloud gates (AKS section).
