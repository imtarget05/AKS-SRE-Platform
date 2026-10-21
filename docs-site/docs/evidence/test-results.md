# Reproducible checks and their limits

The numbers below are from this repository only. Other portfolio projects
must be checked at their own commit; this page does not reproduce their test
output or aggregate their vulnerability scans.

| Check | Result at AKS-SRE-Platform HEAD `62c901f` | Reproduce |
|---|---|---|
| Gate regression script | **47 assertions passed, 0 failed** on 2026-10-21 | `.venv/bin/python tests/test_gates.py` |
| Envoy Gateway kustomize root | Rendered successfully; syntax/composition only | `kubectl kustomize platform/envoy-gateway/gateway >/dev/null` |
| LegacyApp reference workload | **4 tests passed**; `/sync` is a no-op | `cd apps/legacy-inventory/src && npm test` |
| GitOps source validator | Historical **16 passed / 0 failed / 2 not-present**, per current task log | `python3 gitops/validate-gitops.py` |

The gate script is `tests/test_gates.py`; there is no
`tests/test_gate_matrix.py` in this repository. A green render or unit test
does not prove live AKS deployment or operational reliability. For the
environment-labelled claim table, see
[current state](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/engineering/CURRENT_STATE.md)
and the [audit matrix](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/evidence/portfolio-audit-2026-10-21.md).
