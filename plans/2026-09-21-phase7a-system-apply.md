# Phase 7A SYSTEM-ONLY APPLY — Focus Plan (2026-09-21)

STATUS: SYSTEM-ONLY APPLY 🟢 APPROVED (strictly limited). User pool / proofs / Argo CD / ingress / P01-P02 🔒.

Scope (exactly 3 managed resources):

1. `azurerm_resource_group.aks` — rg-aks-platform-dev, eastasia
2. `azurerm_kubernetes_cluster.aks` — aks-portfolio-dev, 1.36, Free, sys 2×D4as_v5 Regular autoscale OFF, only_critical_addons ON, OIDC+WI ON, LB Standard/loadBalancer, no LAW
3. `azurerm_role_assignment.aks_acr_pull` — AcrPull (classic) kubelet identity → acrflashsalep6

## A. Freeze (trước plan cuối)

Commit source-of-truth: `terraform/aks-foundation/**`, `.terraform.lock.hcl` (bỏ ignore `**/.terraform.lock.hcl`), `.gitignore`, ADR-012, evidence sanitized (`plan.txt`, `plan-summary.md`, `cost.md`), `tasks/current.md`, `plans/**`.
Cấm: `plan.out`, `plan.json`, `*.tfplan`, `.local/`, `.terraform/`, tfstate, secrets.
Ghi `git rev-parse HEAD` làm source commit. Không gồm WIP ngoài lề.

## B. Live safety (recheck)

`az account show`; `az vm list-usage --location eastasia`; `list-skus Standard_D4as_v5` unrestricted; `az aks get-versions --location eastasia` còn 1.36; `az aks list` chưa có aks-portfolio-dev; `az acr show -n acrflashsalep6` admin false + LegacyRegistryPermissions. Lệch → STOP.

## C. Init (không upgrade)

`terraform init -input=false`; `fmt -check -recursive`; `validate`; lock giữ 5.6.0. Cấm `init -upgrade`.

## D. Saved plan

`mkdir -p .local` (gitignored); `terraform plan -input=false -out=.local/phase7a-system.tfplan`; `terraform show` + JSON khi cần. Không commit.

## E. Hard gate

`Plan: 3 to add, 0 to change, 0 to destroy`; đúng 3 resources trên (data source read OK); shape khớp A (region/cluster/1.36/sys/D4as_v5×2/Regular/OFF/ON/OIDC+WI/LB/outbound, no user pool/LAW). Sai → STOP.

## F. Apply

Chỉ khi gate pass: `terraform apply .local/phase7a-system.tfplan`. Cấm `apply` không kèm saved plan. Ghi start/end/duration.

## G–M. Verify + stop

State list đúng 3 (+data read, không helm/app); live AKS Running, 2 nodes Ready D4as_v5 System Regular, kube-system healthy; OIDC/WI foundation ON (chưa tạo test pod); RBAC kubelet→AcrPull qua CLI (không admin/secret/manual assignment; chưa pull proof); cost inventory incl. node RG + quota ~8/10; `az aks stop` → Stopped (spend không zero).

## N. Cấm

Không `enable_workload_pool=true`, D2as_v5, pull/WI pod test, P01/P02, Argo CD, ingress, DB/messaging. Approval riêng sau.

## Acceptance

`# PHASE 7A SYSTEM FOUNDATION REPORT` đầy đủ Source Commit→Gate PASS/FAIL/BLOCKED→NEXT (user pool proof, KHÔNG implement). STOP.
