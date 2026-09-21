# Phase 7A — Dsv6 quota-recovery preflight (fresh live checks, 2026-09-21)

Source commit: `e9d086c` (P0 structural safety, no repo restructuring during recovery)
Region: **eastasia** · Scope: AKS foundation only · **No apply performed.**

## Attempt 1 (preserved as history — not rewritten)

| Field | Value |
|---|---|
| SKU | `Standard_D4as_v5` |
| Family | `standardDASv5Family` |
| Regional quota | 0 / 10 (remaining 10) |
| Family quota | **0 / 0** (remaining 0) |
| Error | `ErrCode_InsufficientVCPUQuota` — "requested 8, remaining 0 for family standardDASv5Family for region eastasia" |
| Cost incurred | ≈ $0 (RG only, empty; no cluster, no compute) |

**Lesson:** `az vm list-skus Restrictions=[]` only means the SKU exists in the
region — it is **not** entitlement. Deployment feasibility =
SKU availability **+ VM-family quota + regional quota + regional/zone capacity
+ AKS support**. Azure enforces regional total **and** VM-family quota
concurrently; missing either blocks the deployment.

## Fresh preflight (this recovery, both quota tiers)

| Tier | Used / Limit | Remaining | Requirement | Result |
|---|---|---|---|---|
| Regional total (`cores`) | 0 / 10 | **10** | ≥ 8 | PASS |
| `StandardDsv6Family` | 0 / 10 | **10** | ≥ 8 | PASS |

All v5 D-families remain `0/0` (DASv5, DSv5, DDSv5, DDv5, Dv5, DPSv5, …) —
the family cap that blocked attempt 1 is unchanged. v6 families (Dsv6, Ddsv6,
Dlsv6, Dpsv6, …) all report `0/10`.

## Exact SKU (live `az vm list-skus --location eastasia`)

| Field | Value |
|---|---|
| SKU | `Standard_D4s_v6` |
| Family | `StandardDsv6Family` |
| vCPU | **4** |
| RAM | **16 GiB** |
| Restrictions | `[]` |
| Zones | `1, 2, 3` |

Requirement ≥ 4 vCPU / 4 GB per node (AKS system-pool minimum, ≥2 nodes): PASS.

## Other gates

| Check | Result |
|---|---|
| AKS `1.36` offered in eastasia | PASS (`az aks get-versions` → 1.36 present) |
| `aks-portfolio-dev` absent | PASS (`az aks list` → 0 clusters) |
| RG `rg-aks-platform-dev` exists, empty | PASS (eastasia, tags intact) |
| ACR `acrflashsalep6` | PASS (Standard, admin **disabled**, public access Enabled) |

## Not-yet-authorized SKU

`Standard_D2s_v6` (2 vCPU / 8 GiB, `Restrictions=[]`, $0.139/h) is the intended
**temporary** user pool. It is **NOT** created now and this file does **not**
claim future capacity for it — both quota tiers must be re-checked immediately
before that pool is created.

## Quota projection after the expected apply

| Tier | Projected | Headroom |
|---|---|---|
| Regional | 8 / 10 | 2 vCPU |
| `StandardDsv6Family` | 8 / 10 | 2 vCPU |

Projection only — not a reservation. If a later create returns
`AllocationFailed` / capacity error, **do not** auto-bump SKU or change region:
STOP and re-review (quota ≠ capacity).
