# Evidence — Manifest Inventory (P3.7)

| Field | Value |
|-------|-------|
| task | P3.7 — Setup docs/evidence/2026-10-29/ (AKS manifest inventory) |
| commit SHA | 513df730776939c15895eaa56e77e60b27a823a7 |
| command | `gitops/validate-gitops.py` (manifest-inventory check) + review of `MANIFEST-INVENTORY.md` |
| output | Every `*.yaml`/`*.yml` under `kubernetes/` classified (`RENDERED` / `LEGACY_NOT_DEPLOYED` / `EXTERNAL_WORKLOAD_REFERENCE` / `SUPERSEDED` / `REFERENCE_NOT_RENDERED` / `FUTURE_PHASE`); `platform/observability/` corrected from `RENDERED` to `REFERENCE_NOT_RENDERED`; no silent orphans. |
| status | PASS |
| evidence file | `manifest-inventory.md` (symlink → `MANIFEST-INVENTORY.md`) |

## Classification summary

- `kubernetes/` — legacy tree: 6 files classified (1 RENDERED, 2 LEGACY_NOT_DEPLOYED, 1 EXTERNAL_WORKLOAD_REFERENCE, 1 SUPERSEDED, 1 RENDERED root kustomization)
- `platform/` — cluster platform: envoy-gateway + argocd RENDERED; observability dashboards/ServiceMonitors/prometheusrule RENDERED; Helm values LEGACY_NOT_DEPLOYED
- `app/` and `deploy/`: FUTURE_PHASE (F)
