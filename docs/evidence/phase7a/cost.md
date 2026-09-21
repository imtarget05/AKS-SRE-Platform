# Phase 7A Cost Evidence — 2026-09-21

Source: Retail Prices API (`AP East` = eastasia, Consumption, Linux) queried live 2026-09-21 + `docs/evidence/phase7a/plan.txt` (2 adds: AKS + ACR role assignment; RG already in state; data source read).

## SKUs (verified in plan)

- System pool `sys`: 2 × `Standard_D4s_v6` (4 vCPU / 16 GiB, premiumIO, x64), regular, autoscaling OFF
- User pool `work`: gated `enable_workload_pool=false` → count 0 in this plan
- Tier: AKS Free. LB: Standard. Monitoring: OFF.
- History: `Standard_D4as_v5` BLOCKED at apply (`ErrCode_InsufficientVCPUQuota`, DASv5 family 0/0) — see `apply-2026-09-21-BLOCKED.md`. Eastasia offers no v4 D-series (only v5/v6), so v6 selected.

## Unit prices (Consumption, AP East / eastasia, live 2026-09-21)

| SKU | USD/h |
|---|---|
| Standard_D4s_v6 | 0.277 |
| Standard_D4ads_v6 | 0.316 |
| Standard_D4ds_v6 | 0.343 |
| Standard_D4as_v5 (blocked) | 0.422 |
| Standard_D2s_v6 (future proof pool) | 0.139 |

## Burn math

| Phase | Compute |
|---|---|
| Steady state (this plan: 2×0.277) | **0.554 USD/h** ≈ 13.3 USD/day if left running (−34% vs D4as_v5) |
| Proof window (later, +1×0.211 temporary) | **0.765 USD/h** for minutes only, then delete pool same session |
| Stopped (`az aks stop`) | compute ≈ 0; disks + public IP + Standard LB remain (small, ongoing) |

## Guardrails

- Budget alerts 50/75/90/100% are notifications, not a cap — real cap = stop discipline.
- Quota eastasia regular 10 vCPU: this plan uses 8/10; proof window hits 10/10 then back to 8/10 after pool delete.
- Do not leave cluster running unattended. Stop after session: `az aks stop -g rg-aks-platform-dev -n aks-portfolio-dev`.
