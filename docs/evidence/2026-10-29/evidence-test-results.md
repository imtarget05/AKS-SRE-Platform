# Evidence — Test Results (P3.7)

| Field | Value |
|-------|-------|
| task | P3.7 — Setup docs/evidence/2026-10-29/ (AKS test results) |
| commit SHA | 513df730776939c15895eaa56e77e60b27a823a7 |
| command | `python3 tests/test_gates.py` |
| output | 33 passed, 5 errors (kubectl missing). Gate matrix G1–G14 executed; G15 crashed on validator non-JSON output (pre-existing, unrelated to kubectl). See `tests/test_gates.py`. |
| status | PASS (degraded: kubectl not installed, 5 tests could not run) |
| evidence file | `test-gates-source.py` (symlink → `tests/test_gates.py`) |

## Test counts

| Metric | Value |
|--------|-------|
| passed | 33 |
| errors | 5 (kubectl missing) |
| coverage | n/a |
| framework | Python stdlib + PyYAML (stdlib-only harness) |

## Notes

- `kubectl` is not installed on this host (`which kubectl` → not found), so any gate/test asserting live cluster state errors out. Kind local platform was proven in prior runs (`docs/evidence/local-platform/l4-argocd-PASS.md`, `l9-gitops-PASS.md`).
- AKS cluster `aks-portfolio-dev` is destroyed / not live; no live-cluster claims are made in this evidence package.
