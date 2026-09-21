# Phase 7A Cost Evidence — 2026-09-21

Source: `docs/adr/012-aks-foundation-cost-safe.md:112-152` (Azure Retail Prices API, eastasia, Consumption) + `docs/evidence/phase7a/plan.txt:134` (3 adds: RG + AKS + ACR role assignment; data source là read).

## SKUs (verified in plan)

- System pool `sys`: 2 × `Standard_D4as_v5` (4 vCPU / 16 GiB), regular, autoscaling OFF
- User pool `work`: gated `enable_workload_pool=false` → count 0 in this plan
- Tier: AKS Free. LB: Standard. Monitoring: OFF.

## Unit prices (Consumption, eastasia)

| SKU | USD/h |
|---|---|
| Standard_D4as_v5 | 0.422 |
| Standard_D2as_v5 | 0.211 |

## Burn math

| Phase | Compute |
|---|---|
| Steady state (this plan: 2×0.422) | **0.844 USD/h** ≈ 20.3 USD/day if left running |
| Proof window (later, +1×0.211 temporary) | **1.055 USD/h** for minutes only, then delete pool same session |
| Stopped (`az aks stop`) | compute ≈ 0; disks + public IP + Standard LB remain (small, ongoing) |

## Guardrails

- Budget alerts 50/75/90/100% are notifications, not a cap — real cap = stop discipline.
- Quota eastasia regular 10 vCPU: this plan uses 8/10; proof window hits 10/10 then back to 8/10 after pool delete.
- Do not leave cluster running unattended. Stop after session: `az aks stop -g rg-aks-platform-dev -n aks-portfolio-dev`.
