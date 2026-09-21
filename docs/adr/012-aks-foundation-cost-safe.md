# ADR-012 — AKS Foundation Architecture (system pool + temporary user pool)

- Status: **PROPOSED (v2) — NOT APPLIED.** Cost Safety Mode: apply happens only
  after the user re-approves this revised version. `rg-aks-platform-prod` /
  `rg-aks-platform-dev` do not exist (`az group exists` → false); the RG name in v2
  is `rg-aks-platform-dev` per the non-prod naming correction.

## Context

Phase 7A needs one minimal Azure/Kubernetes foundation for P01 + P02:
nodes Ready, private ACR pull working, OIDC + Workload Identity plumbing
proven — and nothing else (no PostgreSQL/Redis/RabbitMQ/Argo CD/ingress/
monitoring in 7A).

## Live subscription facts (queried, not assumed)

| Fact | Value (source) |
|---|---|
| Region | `eastasia` — chosen over `southeastasia` for a documented reason below |
| southeastasia SKU status | every candidate SKU (D2s_v3/v5, D2as_v5, D4s_v5/as_v5) is `NotAvailableForSubscription` **at Location + Zone scope** — a subscription block, not capacity |
| Regions checked | `eastasia`: D2as_v5 / D2s_v5 / D4s_v5 → **NO RESTRICTIONS**; `australiaeast`, `australiasoutheast`: same; `japaneast`: query timed out (unresolved, not selected) |
| Quota (eastasia) | regular 0/10, Spot 0/3 — identical to southeastasia |
| AKS versions | 1.36.x line (`1.36.3` latest; Official + LTS tracks) |
| AKS docs (current) | production single-system-pool cluster: **≥ 2 nodes** (3 recommended) |
| Existing clusters | `az aks list` → none |

## Decision (v1, proposed)

```text
RG rg-aks-platform-dev               (new, eastasia, non-prod name)
## Architecture (v2 ASCII — revised per corrections)

```text
          eastasia
            │
    ┌───────┴─────────────────────────────────┐
    │ RG rg-aks-platform-dev (non-prod name)  │
    └───────────────┬─────────────────────────┘
                    │
              AKS aks-portfolio-dev
              (k8s 1.36.x pinned, Free tier,
               OIDC issuer + Workload Identity)
                    │
              ┌─────┴──────────────────────────┐
              │  system pool "sys"             │  2 × Standard_D4as_v5 (4 vCPU/16 GiB each)
              │  regular · mode=System         │  system components only
              └─────┬──────────────────────────┘
                    │
              ┌─────┴──────────────────────────┐
              │  user pool "work" (TEMPORARY)  │  1 × Standard_D2as_v5 (2 vCPU/8 GiB)
              │  regular · mode=User           │  placement + private ACR pull proof,
              │  deleted same-session          │  then az aks nodepool delete
              └────────────────────────────────┘
```

## Load balancer + networking notes

- `load_balancer_sku = "standard"` explicit — Basic LB retired 2025-09-30;
  AKS creates a Standard LB + one public IP for the API server (documented
  Portfolio setting; private cluster is an enterprise reference).
- No application LoadBalancers/Ingress in 7A (they belong to 7B).


└── AKS aks-portfolio-dev             (k8s 1.36.x pinned, Free tier, OIDC + WI enabled)
    ├── system pool "sys"             Standard_D4as_v5, 2 nodes, regular, mode=System
    └── user pool "work" (TEMPORARY)  Standard_D2as_v5, 1 node, regular, mode=User,
                                      created ONLY for the 7A placement + pull tests,
                                      deleted immediately after evidence is captured
```

Why eastasia (documented, not silent): candidate SKUs are subscription-blocked
in southeastasia at Location scope, unrestricted in eastasia with identical
quota. Existing resources (ACR, backups, state) stay put; multi-region is a
documented Phase-10 consideration.

Why this SKU mix (v2 correction): system pool needs a valid unrestricted
general-purpose VM with **≥ 4 vCPU / 4 GB** per the docs minimum —
`Standard_D2s_v5` (2 vCPU / 8 GiB) was therefore REJECTED. Live price
comparison (Azure Retail API, eastasia): `D4as_v5` 0.422 vs `D4s_v5` 0.448
USD/h → **`Standard_D4as_v5` ×2 (cheapest 4-vCPU candidate, unrestricted,
4 vCPU / 16 GiB each)**. The user pool keeps `Standard_D2as_v5` ×1 as a
*different* SKU so one capacity hiccup cannot block the cluster.

Why a TEMPORARY user pool instead of skipping it: 7A must prove (a) a test pod
lands on the user pool and (b) kubelet RBAC pulls a private ACR image. A
placement assertion on paper is not evidence — but the pool exists only for
the proof and `az aks nodepool delete` is part of the acceptance sequence,
returning the footprint to the cheapest steady state.

Excluded from v1 (cost control): no autoscaler (would add nodes unattended),
no Spot (Phase 11 subject), no new Log Analytics workspace (Container Insights
OFF for 7A; logs stay in-cluster / `kubectl logs`), no ingress/LB beyond AKS
defaults, no monitoring stack, no Kafka, no application workloads.

## Cost Preflight v2 — REVISED per user correction (East Asia live prices)

User corrections applied: system SKU must be ≥ 4 vCPU / 4 GB (not D2s_v5),
compare D4s_v5 vs D4as_v5 on price, Standard Load Balancer (Basic retired
2025-09-30), RG name non-prod, and quota headroom issue re-checked.

### East Asia live quota (re-queried after approval)

```text
Total Regional vCPUs                0 / 10
Total Regional Low-priority vCPUs   0 / 3
```

`az vm list-skus` (eastasia): `Standard_D4s_v5`, `Standard_D4as_v5`,
`Standard_D2as_v5` → Restrictions: **[] (none)**. AKS versions: up to 1.37
(default stream) — pinned explicitly in Terraform to avoid a silent bump.

### Live price comparison (Azure Retail Prices API, eastasia, Consumption)

```text
Standard_D4s_v5    0.448 USD/h   (Consumption)   0.264 USD/h DevTest*
Standard_D4as_v5   0.422 USD/h   (Consumption)   0.238 USD/h DevTest*
Standard_D2as_v5   0.211 USD/h   (Consumption)   0.119 USD/h DevTest*
```

(*) DevTestConsumption meters apply only to subscriptions flagged Dev/Test —
verified flag presence in the price table; the safe number is the Consumption
price unless confirmed otherwise.

→ **Cheapest 4-vCPU candidate: `Standard_D4as_v5` at 0.422 vs 0.448 USD/h
(≈6 % cheaper; AMD) — both unrestricted, same 4 vCPU / 16 GiB.**

### v1 corrections applied

| v1 (rejected) | v2 (this version) | Why |
|---|---|---|
| system `D2s_v5` ×2 (2 vCPU) | system `Standard_D4as_v5` ×2 | docs minimum 4 vCPU / 4 GB per node; cheapest live 4-vCPU SKU |
| user `D2as_v5` permanent | user `D2as_v5` ×1 **temporary**, deleted same-session after proof | user pools are cheaper-tested but the quota must not stay saturated |
| quota math “6/10” | **10/10 during proof, 4/10 after user pool deleted** | honest recount (8 + 2 = 10) — zero headroom while proving |
| Basic LB | `load_balancer_sku = "standard"` explicit | Basic LB retired 2025-09-30 |
| `rg-aks-platform` | `rg-aks-platform-dev` | non-prod naming |

### Headroom plan (quota, not budget)

While the temporary user pool exists, regular vCPU is at the 10/10 limit.
Mitigations chosen: (a) the pool lives for minutes — placement test + ACR pull
test in one session — then `az aks nodepool delete`; (b) if a mid-proof failure
needs a third node, the pool is deleted and retried rather than scaled; (c)
quota-increase request (free, to ~16) is only filed if repeated retries prove
the single-session flow is unreliable.

### Price math (Consumption)

| Phase | Compute burn |
|---|---|
| Proof window (system 2×0.422 + user 1×0.211) | **1.055 USD/h** for the minutes it takes to run the two tests |
| Steady state (system 2×0.422) | **0.844 USD/h** ≈ 20.3 USD/day if left running — hence the stop/start discipline |
| Stopped (`az aks stop`) | compute ≈ 0; disks + public IP + LB remain (small, ongoing) |

Budget-safety note: Budget alerts (50/75/90/100 %) are recommended before any
apply, but they are notifications, not a cap — the real cap is the stop discipline.

## Rollback / cleanup commands (v2 names)

```bash
az aks nodepool delete -g rg-aks-platform-dev --cluster-name aks-portfolio-dev --name work
az aks stop  -g rg-aks-platform-dev -n aks-portfolio-dev
az aks start -g rg-aks-platform-dev -n aks-portfolio-dev
```

## Alternatives rejected

- southeastasia `Standard_D2s_v3` × 2 (old repo-03 default): blocked —
  subscription-level `NotAvailableForSubscription` on every D SKU there.
- 3-node system pool: docs-recommended for production, but v1 optimises for
  credit; the docs minimum (≥ 2) is honoured.
- Spot user pool now: belongs to Phase 11 cost experiments, not a correctness baseline.
- Premium/burstable SKUs, extra pools, autoscaler: credit-inefficient for the proof.

## Addendum 2026-09-21 — quota recovery (D4as_v5 → D4s_v6)

- D4as_v5 attempt **BLOCKED** at apply: `ErrCode_InsufficientVCPUQuota` — quota is two-tier
  (regional total AND per-family); regional was 0/10 but `standardDASv5Family` = 0/0 eastasia.
  Evidence: `docs/evidence/phase7a/apply-2026-09-21-BLOCKED.md`.
- Eastasia offers **no v4 D-series** for this subscription (`list-skus --size D4s/D4as` → v5/v6 only),
  so all four v4 candidates were ineligible at the region level.
- Replacement: **`Standard_D4s_v6`** — cheapest eligible (Dsv6 family quota 10, AKS-allowlisted,
  Restrictions None, 4 vCPU / 16 GiB, premiumIO, $0.277/h AP East Consumption vs $0.422/h D4as_v5).
  System steady state drops 0.844 → **0.554 USD/h** (−34%).
- Pre-existing condition found during refresh: `stflashs3ctfbk01` firewall is Deny with a stale
  single-IP allowlist; residential IP rotation caused 403 on state load. Added current IP only
  (auditable, reversible). Residual risk: recurring on every IP change — consider VPN/allowlist
  automation or private endpoint before Phase 10.
