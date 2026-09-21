# Phase 7A Quota Recovery — Focus Plan (2026-09-21)

STATUS: NOT YET APPROVED FOR APPLY. Recovery from BLOCKED apply (`ErrCode_InsufficientVCPUQuota`, DASv5 0/0).
Option: **Option 2 — đổi SKU sang family còn quota**, không xin quota, không destroy RG, không reuse saved plan cũ.

## Current actual state (verified)

- State: `data.azurerm_container_registry.shared` + `azurerm_resource_group.aks`. AKS absent, role absent.
- RG `rg-aks-platform-dev`: exists, empty, ~0 cost. Preserve.
- Stale: `.local/phase7a-system.tfplan` — DO NOT reuse.
- Current SKU: `Standard_D4as_v5` (family DASv5 = 0/0 eastasia) — rejected.

## STEP1 — Preflight (done live 2026-09-21)

Gate mới: SKU available + Restrictions=[] + family quota ≥8 + regional ≥8 + price acceptable.

Key finding: **eastasia không còn v4** (`--size D4s/D4as` chỉ trả v5/v6). 4 candidate gốc (D4as_v4, D4s_v4, D4_v4, D4s_v3) **không tồn tại ở region** → loại toàn bộ.

Pivot sang v6 (family quota 10/10, AKS allowlist Restrictions None):

| SKU | Family | vCPU/RAM | Family quota | Restrictions | $/h (AP East) | $/h x2 | Eligible |
|---|---|---|---|---|---|---|---|
| Standard_D4s_v6 | Dsv6 | 4/16, premiumIO | 10 | None | 0.277 | 0.554 | YES — selected |
| Standard_D4ads_v6 | Dadv6 | 4/16, premiumIO | 10 | None | 0.316 | 0.632 | YES — đắt hơn |
| Standard_D4ds_v6 | Ddsv6 | 4/16, premiumIO | 10 | None | 0.343 | 0.686 | YES — đắt hơn |
| Standard_D4as_v5 | DASv5 | 4/16 | **0** | n/a | 0.422 | 0.844 | NO — quota 0 |

## STEP2 — Selection: Standard_D4s_v6

Rẻ nhất ($0.277/h, −34% vs D4as_v5), Intel x64, premiumIO=True, AKS-allowlisted, Dsv6 quota 10, regional 0/10.

## STEP3 — Architecture unchanged

Chỉ đổi VM size. Giữ: eastasia, RG, cluster name, 2 nodes Regular, autoscaler OFF, Spot OFF, critical-addons ON, k8s 1.36, OIDC+WI, LB standard/loadBalancer, ACR + AcrPull, no user pool/LAW/Helm/apps.

## STEP4 — Refresh state

`init -input=false` (no -upgrade), `state list`, `plan -refresh-only`: RG managed, AKS/role absent, no drift/destroy.

## STEP5 — SKU-only change

`system_pool_vm_size` → `Standard_D4s_v6`. Update cost docs + ADR (ghi D4as_v5 BLOCKED + lý do). Không đụng infra khác.

## STEP6 — Replan (new saved plan)

Xóa/bỏ stale plan. `plan -out=.local/phase7a-quota-recovery.tfplan` (gitignored).
Expected (RG đã trong state): **2 to add / 0 / 0** (AKS + role; RG Chandler already exists — no recreate/destroy).
Destroy>0 / RG replace / resource lạ → STOP.

## STEP7 — REVIEW + STOP

Trả `# PHASE 7A QUOTA RECOVERY PRE-APPLY REVIEW` (failure, comparison, selected, state, RG, plan, quota-after, headroom, arch-change=SKU-only, risks, DECISION). **DO NOT APPLY.**
