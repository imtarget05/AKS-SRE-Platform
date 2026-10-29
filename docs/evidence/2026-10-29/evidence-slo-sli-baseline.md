# Evidence — SLO / SLI Baseline (P3.7)

| Field | Value |
|-------|-------|
| task | P3.7 — Setup docs/evidence/2026-10-29/ (AKS SLO/SLI baseline) |
| commit SHA | 513df730776939c15895eaa56e77e60b27a823a7 |
| command | `scripts/measure_sli_30day.py` + in-cluster probe Job `sli-probe-baseline` (30 sequential GETs per endpoint, `curl -w time_total`) |
| output | availability 100.0000% (target 99.9%), latency_p95 54.55ms opsbridge / 15.21ms bankops (target < 500ms), error_rate 0.0% (target < 1%). All SLIs PASS on captured sample. |
| status | PASS |
| evidence file | `slo-baseline-2026-10-26.json` (symlink → `docs/evidence/2026-10-26/slo-baseline-2026-10-26.json`), `sli-probe-raw-output.txt` (symlink → `docs/evidence/2026-10-26/sli-probe-raw-output.txt`), `slo-baseline-README.md` (symlink → `docs/evidence/2026-10-26/slo-baseline-README.md`) |

## SLI definitions

| SLI | Target | Measured | Status |
|-----|--------|----------|--------|
| availability | >= 99.9% (30-day) | 100.0000% | PASS |
| latency_p95 | < 500ms | 54.55ms (opsbridge) / 15.21ms (bankops) | PASS |
| error_rate | < 1% (5xx) | 0.0% | PASS |

## SLO docs (already present)

- `deploy/sli/availability.md`, `deploy/sli/error_rate.md`, `deploy/sli/latency_p95.md`
- `deploy/slo/availability.md`, `deploy/slo/error_rate.md`, `deploy/slo/latency_p95.md`
