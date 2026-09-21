# Phase 7A Correction — 3 Fixes (Plan Only, NOT YET APPROVED FOR APPLY)

Ngày: 2026-09-21
Trạng thái: PLAN — NOT YET APPROVED FOR APPLY (USER APPROVAL REQUIRED)
Scope: `terraform/` — correction trên nền Phase 7A foundation
Base plan: `plans/2026-09-21-phase7a-aks-foundation.md`

RESULT: PARTIAL — plan correction đã mô tả đầy đủ 3 fixes + verification + acceptance, chờ user approval trước khi apply. Chưa chạy `terraform apply`.

> Không spawn subagent cho plan correction này.

## 1. Goal — NOT YET APPROVED FOR APPLY

Khắc phục 3 vấn đề phát hiện sau Phase 7A, sau đó replan sạch. Tuyệt đối **không chạy `terraform apply`** cho đến khi có approval rõ ràng từ user:

1. **FIX1 — Provider `azurerm ~> 5.0`:** nâng constraint, chạy `init -upgrade`, fix mọi breaking change.
2. **FIX2 — Hygiene plan artifact:** unstage `plan.out` / `plan.json`, `.gitignore` `*.tfplan` / `plan.out` / `plan.json`, giữ `plan.txt` / `cost.md`, tạo `plan-summary.md` sanitized.
3. **FIX3 — ACR `acrflashsalep6` + RBAC kubelet:** query ACR mode classic vs ABAC, rồi data source + `azurerm_role_assignment` AcrPull (hoặc Repository Reader) cho kubelet identity.

Preserve toàn bộ baseline Phase 7A:
- RG `rg-aks-platform-dev` / cluster `aks-portfolio-dev` / k8s `1.36`
- Sys pool `2x Standard_D4as_v5` / LB `standard` / OIDC + WI bật
- Remote-state check `use_azuread_auth`
- Replan pipeline: `fmt` → `init -upgrade` → `validate` → `plan`

## 2. FIX1 — azurerm `~> 5.0` + `init -upgrade` + fix breaking

- Đổi `required_providers.azurerm` version constraint sang `~> 5.0` trong `terraform/` (file versions/backend).
- Chạy `terraform init -upgrade` (backend azurerm giữ nguyên: `rg-flashsale-tfstate` / `stflashs3ctfbk01` / `tfstate` / `aks-foundation.terraform.tfstate`).
- Fix mọi breaking change do major 5.x gây ra (removed/deprecated arguments, provider schema, `use_azuread_auth` / auth block nếu đổi tên).
- Chạy lại `terraform fmt` + `terraform validate` — cả hai phải pass trước khi sang FIX2/FIX3.

## 3. FIX2 — Unstage plan.out/plan.json, .gitignore, giữ plan.txt/cost.md + plan-summary.md sanitized

- `git restore --staged` (hoặc `git rm --cached`) mọi `plan.out` / `plan.json` / `*.tfplan` nếu đã stage — các file này **NOT committed**.
- Thêm vào `.gitignore` (repo hoặc `terraform/.gitignore`):
  ```
  *.tfplan
  plan.out
  plan.json
  ```
- Giữ lại trong `docs/evidence/phase7a/`: `plan.txt` (human-readable, `terraform show -no-color`) + `cost.md` (ước tính tay).
- Tạo `docs/evidence/phase7a/plan-summary.md` **sanitized** (không secret, không subscription ID / tenant ID / principal ID thô nếu nhạy cảm): tóm tắt plan counts, resource list, cost, fmt/validate status, link tới `plan.txt`.
- Verify `git status --short` không còn hiện `plan.out` / `plan.json` / `*.tfplan` sau khi ignore.

## 4. FIX3 — Query ACR `acrflashsalep6` (classic vs ABAC) + data source + role assignment cho kubelet identity

- Query ACR `acrflashsalep6` hiện tại: xác định mode **classic (admin/disabled, role-based)** vs **ABAC (repository-scoped permissions)** — ghi lại `sku`, `admin_enabled`, `anonymous_pull_enabled`, `data_endpoint_enabled`, `public_network_access`, `policies`.
- Thêm `data "azurerm_container_registry" "app" { name = "acrflashsalep6" ... }` (dùng RG đúng của ACR, không hardcode subscription nếu đã có provider sub).
- Thêm `azurerm_role_assignment` cho **kubelet identity** của `azurerm_kubernetes_cluster.aks`:
  - Ưu tiên `AcrPull` (classic, đơn giản, đủ cho Phase 7A pull image).
  - Hoặc `Container Registry Repository Reader` nếu ACR đang ở ABAC / cần repository-scoped.
  - `principal_id = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id`, `scope = data.azurerm_container_registry.app.id`, `skip_service_principal_aad_check = true` nếu cần.
- Đây là resource thứ 3 giải thích plan đi từ **2 lên 3 Add** (RG + AKS + role assignment; ACR là data source, không tính add).

## 5. Replan pipeline (sau cả 3 fixes)

1. `terraform fmt -check` (fail → `terraform fmt` rồi check lại).
2. `terraform init -upgrade` (xác nhận azurerm 5.x đã cài).
3. `terraform validate` (phải pass).
4. Remote-state check: xác nhận backend azurerm + `use_azuread_auth` đúng (không chuyển sang access key nếu policy yêu cầu AAD).
5. `terraform plan -out=tfplan -input=false`:
   - `terraform show -no-color tfplan > docs/evidence/phase7a/plan.txt`
   - `terraform show -json tfplan` chỉ dùng tạm để đếm `resource_changes`, **không commit** plan.json/plan.out.
   - Cập nhật `docs/evidence/phase7a/cost.md` + `plan-summary.md` sanitized.
6. **STOP — không `apply`.**

## 6. Verification

- [ ] `fmt` pass (`terraform fmt -check -recursive -diff` exit 0).
- [ ] `validate` pass (`Success! The configuration is valid`).
- [ ] `plan` = **Add 3 Change 0 Destroy 0** — giải thích từ 2 lên 3: `azurerm_resource_group.aks` + `azurerm_kubernetes_cluster.aks` + `azurerm_role_assignment.acr_pull` (ACR là data source, không add).
- [ ] `plan.out` / `plan.json` / `*.tfplan` **NOT committed** (`git status --short` + `git ls-files` kiểm chứng, `.gitignore` đã chặn).
- [ ] RBAC **terraform-managed** (role assignment nằm trong state, không gán tay bằng `az role assignment create` / portal).

## 7. Acceptance Criteria

- Block **FINAL PRE-APPLY REVIEW v2** dưới đây được điền đầy đủ bằng evidence thực tế sau replan.
- **STOP — no apply** cho đến khi user phê duyệt rõ ràng.

## 8. FINAL PRE-APPLY REVIEW v2 (2026-09-21, evidence thực tế — STOP, chưa apply)

- Provider: azurerm constraint `~> 5.0`, locked **5.6.0** (`init -upgrade` OK); breaking 5.x fixed (`auto_scaling_enabled` rename + `node_provisioning_profile Manual`); `fmt -check` PASS, `validate` Success.
- RemoteState: backend `rg-flashsale-tfstate/stflashs3ctfbk01/tfstate` key `aks-foundation.terraform.tfstate`, `use_azuread_auth = true`, không access_key/SAS/secret trong tf và plan. Auth method: Azure CLI + Entra ID (ghi method, không in credentials).
- ACR: `acrflashsalep6` (`rg-flashsale-release`, Standard, admin false, publicNet Enabled) — **classic `LegacyRegistryPermissions`** (live `az acr show`), không phải ABAC; `data.azurerm_container_registry.shared` read-only.
- RBAC: `azurerm_role_assignment.aks_acr_pull` — **AcrPull** (classic), scope ACR id, principal kubelet identity object_id (known after apply), terraform-managed; không `az role assignment create` tay; không tạo registry mới; admin giữ disabled.
- Plan: **Plan: 3 to add, 0 to change, 0 to destroy** (`docs/evidence/phase7a/plan.txt:134`). 2→3 vì thêm role assignment (data source là read, work pool count 0).
- Cost: steady **0.844 USD/h**, proof window **1.055 USD/h**, stopped ≈ 0 compute (`cost.md`, ADR-012).
- Hygiene: `plan.out`/`plan.json` cũ còn local nhưng **NOT tracked** (`git ls-files` empty, `check-ignore` match `.gitignore:8-9`); sanitized `plan.txt` + `plan-summary.md` + `cost.md` đầy đủ. Note: apply sau này dùng `plan -out` vào file gitignored tạm thời để guarantee, không commit.
- Destroy = 0: PASS (0 change/destroy; không đụng ACR/backup/identity).
- Quyết định: **STOP — chờ USER APPROVAL trước apply. Chưa chạy `terraform apply`.**
