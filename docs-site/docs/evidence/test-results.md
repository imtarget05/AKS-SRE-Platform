# Reproducible checks and their limits

The numbers below are from this repository only. Other portfolio projects
must be checked at their own commit; this page does not reproduce their test
output or aggregate their vulnerability scans.

| Check | Result at Current HEAD | Reproduce |
|---|---|---|
| Gate regression script (G1–G14) | **47 assertions passed, 0 failed** | `.venv/bin/python tests/test_gates.py` |
| Terraform configuration validation | **Success! Configuration is valid** (0 syntax/provider errors) | `terraform -chdir=terraform/aks-foundation validate` |
| Envoy Gateway kustomize root | Rendered successfully; syntax/composition only | `kubectl kustomize platform/envoy-gateway/gateway >/dev/null` |
| LegacyApp reference workload | **4 tests passed**; `/sync` is a no-op | `cd apps/legacy-inventory/src && npm test` |
| GitOps validator (Standalone mode) | **16 passed / 0 failed / 2 not-present** (advisory, NOT_PRESENT never masked) | `python3 gitops/validate-gitops.py` |
| GitOps validator (Multi-repo mapped) | **18 passed / 0 failed / 0 not-present** (full cross-repo render) | `python3 gitops/validate-gitops.py --repo-map gitops/repo-map.local.yaml` |

The gate script is `tests/test_gates.py`; there is no
`tests/test_gate_matrix.py` in this repository. A green render or unit test
does not prove live AKS deployment or operational reliability. For the
environment-labelled claim table, see
[current state](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/engineering/CURRENT_STATE.md)
and the [audit matrix](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/evidence/portfolio-audit-2026-10-21.md).
