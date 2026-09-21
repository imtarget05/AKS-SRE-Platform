# Phase 7A — AKS Foundation (Plan Only, System-Only)

Ngày: 2026-09-21
Trạng thái: PLAN — CHƯA APPLY (USER APPROVAL REQUIRED)
Scope: `terraform/` — AKS foundation only

## 1. Goal

Tạo **Plan sạch với đúng 2 to add**:
1. `azurerm_resource_group.aks` — `rg-aks-platform-dev` (eastasia)
2. `azurerm_kubernetes_cluster.aks` — `aks-portfolio-dev` (Free, k8s 1.36, OIDC+WI, LB standard)

Không thêm resource nào khác trong Phase 7A.

## 2. Scope Phase 7A — system-only

- System pool `sys`: **2x `Standard_D4as_v5`**, mode System.
- Work pool `work`: định nghĩa trong code nhưng **gated `false`** (count = 0, không tạo node).
- Kubernetes version: **1.36**.
- Region: **eastasia**.
- SKU tier: **Free**.
- Bật **OIDC issuer + Workload Identity (WI)**.
- `load_balancer_sku = "standard"`.
- Không bật monitoring / OMS / Azure Policy / Helm / password / secret trong Phase 7A.

## 3. Backend & Lịch sử

- Backend `azurerm`:
  - `resource_group_name = "rg-flashsale-tfstate"`
  - `storage_account_name = "stflashs3ctfbk01"`
  - `container_name = "tfstate"`
  - `key = "aks-foundation.terraform.tfstate"`
- Giữ `main.tf` cũ làm lịch sử (không xóa history, chỉ refactor/tách file nếu cần, đảm bảo `terraform plan` vẫn sạch 2 add).

## 4. Work Steps

1. `mkdir -p plans docs/evidence/phase7a`
2. Chuẩn hóa code Terraform Phase 7A (RG + AKS system-only, work pool gated).
3. `terraform fmt -check` (phải pass, nếu fail thì `terraform fmt` rồi check lại).
4. `terraform init` (backend azurerm như mục 3).
5. `terraform validate` (phải pass).
6. `terraform plan -out=tfplan -input=false`:
   - Lưu `docs/evidence/phase7a/plan.txt` (`terraform show -no-color tfplan`).
   - Lưu `docs/evidence/phase7a/plan.json` (`terraform show -json tfplan`).
   - Lưu `docs/evidence/phase7a/cost.md` (ước tính tay: sys 2x D4as_v5 + Free tier + LB standard, work pool 0 node).
7. Không chạy `apply` trong Phase 7A.

## 5. Verification (2026-09-21 — pass hết)

- [x] `terraform fmt -check` → pass (exit 0).
- [x] `terraform validate` → pass (`Success! The configuration is valid`).
- [x] `terraform plan` → **Plan: 2 to add, 0 to change, 0 to destroy**.
- [x] `plan.json` xác nhận chỉ 2 `create` (RG + AKS), không có `delete/update`.
- [x] Không xuất hiện Helm / password / monitoring / secret trong plan.
- [x] Evidence đầy đủ trong `docs/evidence/phase7a/`: `plan.txt`, `plan.json`, `plan.out`, `cost.md`.

## 6. Acceptance Criteria

- Evidence file đầy đủ (`plan.txt`, `plan.json`, `cost.md`).
- Có block **FINAL PRE-APPLY REVIEW** dưới đây đã điền kết quả thực tế.
- **STOP trước apply — USER APPROVAL REQUIRED**. Không apply khi chưa có approval rõ ràng.

## 7. FINAL PRE-APPLY REVIEW (2026-09-21, evidence thực tế)

- fmt: PASS (`terraform fmt -check -recursive -diff` exit 0, 2026-09-21)
- validate: PASS (`Success! The configuration is valid`, exit 0)
- plan summary: `Plan: 2 to add, 0 to change, 0 to destroy.` (xem `docs/evidence/phase7a/plan.txt:120`)
- plan resources: `azurerm_resource_group.aks` [create], `azurerm_kubernetes_cluster.aks` [create] (xem `plan.json` resource_changes = 2 creates, node_pool `work` gated count 0)
- cost: steady **0.844 USD/h** (2×0.422), proof window **1.055 USD/h** tạm thời, stopped ≈ 0 compute (xem `docs/evidence/phase7a/cost.md`)
- Quyết định: **STOP — chờ USER APPROVAL trước apply. Chưa chạy `terraform apply`.**

---
Không spawn subagent cho Phase 7A plan này.
