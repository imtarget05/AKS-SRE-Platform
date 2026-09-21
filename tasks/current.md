# AKS-SRE-Platform — Current Tasks

> Updated: 2026-09-21 | Active Goal: **Phase 7A QUOTA RECOVERY (Option 2, NOT YET APPROVED FOR APPLY)**

## ACTIVE GOAL 2026-09-21 — Phase 7A quota recovery

STATUS: NOT YET APPROVED FOR APPLY — ⛔ STOP, no apply until recovery REVIEW passes.
Decision: Option 2 — SKU-only switch (D4as_v5 BLOCKED DASv5 0/0 → **Standard_D4s_v6**, Dsv6 quota 10, $0.277/h). No quota request, no RG destroy, no stale-plan reuse.
Next: refresh state → SKU change → replan `.local/phase7a-quota-recovery.tfplan` (expect 2/0/0) → REVIEW → STOP.

## SUPERSEDED — Phase 7A SYSTEM-ONLY APPLY (APPROVED, strictly limited)

## ACTIVE GOAL 2026-09-21 — Phase 7A SYSTEM-ONLY APPLY

STATUS: 🟢 APPROVED — strictly limited to RG `rg-aks-platform-dev` + AKS `aks-portfolio-dev` + Terraform-managed AcrPull. User pool / proofs / Argo CD / ingress / P01-P02 🔒.

APPLY ATTEMPT 2026-09-21T07:59Z: **BLOCKED** — `ErrCode_InsufficientVCPUQuota` (standardDASv5Family 0/0 eastasia).
Partial state: RG created (empty, ~0 cost), AKS absent. No rerun, no destroy, no VM auto-switch per gate G.
Evidence: `docs/evidence/phase7a/apply-2026-09-21-BLOCKED.md`. Next: user picks quota-increase retry vs SKU-family switch vs RG cleanup.

Next steps: A freeze commit → B live safety → C init (no -upgrade) → D saved plan `.local/phase7a-system.tfplan` → E gate 3/0/0 → F apply exact plan → H–M verify/stop → FINAL REPORT → STOP (no user pool).

## ACTIVE GOAL 2026-09-21 — Phase 7A correction (superseded by apply approval above)

RESULT: PARTIAL — `current.md` updated with Phase 7A correction plan; APPLY BLOCKED pending REVIEW v2.

## ACTIVE GOAL 2026-09-21 — Phase 7A correction

STATUS: NOT YET APPROVED FOR APPLY — ⛔ STOP, no `terraform apply` until REVIEW v2 passes with explicit approval.

3 fixes required:
- FIX1 provider 5.x — bump/pin `azurerm` to 5.x line, `terraform init -upgrade`, re-validate `validate/fmt`.
- FIX2 evidence hygiene — no raw plan files in git; `gitignore` raw plans (`*.tfplan`, `plans/raw/`), only redacted evidence committed.
- FIX3 ACR RBAC terraform-managed + remote-state check — ACR role assignment managed by Terraform (not manual `az` CLI); verify remote-state backend (RG/storage/container/key `aks-foundation.tfstate`, encryption, locking) before replan.

Next steps (in order):
1. query ACR mode → 2. bump provider → 3. gitignore raw plans → 4. RBAC wiring → 5. replan → 6. REVIEW v2 → 7. STOP no apply.

## Lịch sử (giữ nguyên) — Active Goal cũ: Phase 7A AKS Foundation

**Trạng thái hiện tại:**
- [x] P01 PASS — Preflight / repo hygiene checks passed
- [x] P02 PASS — Terraform validate / fmt / structure checks passed
- [ ] NO cluster — Chưa có AKS cluster nào được tạo
- [ ] NO apply authorized — Chưa được phép chạy `terraform apply`

**Gate STOP trước apply:**
> ⛔ STOP — Không chạy `terraform apply` cho đến khi FINAL PRE-APPLY REVIEW (7A.5) hoàn tất và được approve explícit.

## Next Steps 7A.1 – 7A.5

- [x] **7A.1 Refactor done** — Tách module / layout terraform theo chuẩn Phase 7A (done)
- [ ] **7A.2 Providers** — Pin + cấu hình providers (azurerm, kubernetes, helm, null/time):
  - Kiểm tra versions.tf / providers.tf
  - Xác nhận backend config chưa apply
- [ ] **7A.3 Remote state** — Cấu hình remote state (Azure Storage backend):
  - Resource group / storage account / container
  - State key `aks-foundation.tfstate`, encryption, locking
  - `terraform init -migrate-state` dry-check (chưa migrate thật nếu chưa approve)
- [ ] **7A.4 System-only plan** — Chạy `terraform plan` scoped system-only:
  - Chỉ RG + VNet + AKS system nodepool, NO user workloads
  - Lưu plan file, review diff, không apply
- [ ] **7A.5 FINAL PRE-APPLY REVIEW** — Review cuối trước apply:
  - Checklist: P01/P02 evidence, plan output, cost/sku/region, network, auth/RBAC, secrets handling
  - Approve → mới được phép apply. Nếu chưa approve → giữ gate STOP.

## Notes

- `main.tf` cũ **superseded** — đã archive về `terraform/legacy/main.tf.disabled` (P0.1, 2026-09-21): không còn `.tf` runnable ở đó, secret đã xoá khỏi HEAD (P0.2). Active roots: `terraform/aks-foundation` + `terraform/data-protection` (con trỏ, root thật ở P01 `backup-storage`). Xem `terraform/README.md`.
- Helm `admin123` **đã xoá khỏi HEAD** (P0.2, 2026-09-21) — kể cả Secret plaintext trong `kubernetes/keda-trigger-auth.yaml`. Không commit password plaintext; dùng secret reference (Key Vault / External Secrets / Sealed Secrets). Credential cũ nếu từng dùng thật ở env nào → rotate.
- Mọi `apply` đều yêu cầu approval explícit sau 7A.5.
