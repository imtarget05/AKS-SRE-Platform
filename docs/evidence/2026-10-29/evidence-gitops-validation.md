# Evidence — GitOps Validation (P3.7)

| Field | Value |
|-------|-------|
| task | P3.7 — Setup docs/evidence/2026-10-29/ (AKS gitops validation) |
| commit SHA | 513df730776939c15895eaa56e77e60b27a823a7 |
| command | `python3 gitops/validate-gitops.py` (+ `--json`) |
| output | 35/35 GitOps validator checks PASS; AppProject `portfolio` canonical under `platform/argocd/`; no duplicate object declarations; Argo CD pin v3.5.5 in `platform/argocd/VERSION`. |
| status | PASS |
| evidence file | `gitops-l9-PASS.md` (symlink → `docs/evidence/local-platform/l9-gitops-PASS.md`), `argocd-applications.txt` (symlink → `docs/evidence/local-platform/2026-10-21-recreate/argocd-applications.txt`) |

## Summary

- Argo CD Applications: `flashsale` (Synced/Healthy), `legacyapp` (Synced/Healthy) — local kind platform
- Forward deployment + Git revert rollback proven (L9.3/L9.4)
- Validator: `gitops/validate-gitops.py` enforces MANIFEST-INVENTORY.md classification, single AppProject, cross-repo destination allowlisting
- Cloud gates retracted: `cloud-recheck-1427-utc.md` (see P3.9)
