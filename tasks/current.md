# AKS-SRE-Platform — Current Tasks

> Updated: 2026-09-21 | Active Goal: **Phase 7A SYSTEM-ONLY APPLY (APPROVED, strictly limited)**

## ACTIVE GOAL 2026-09-21 — Phase 7A SYSTEM-ONLY APPLY

STATUS: 🟢 APPROVED — strictly limited to RG `rg-aks-platform-dev` + AKS `aks-portfolio-dev` + Terraform-managed AcrPull. User pool / proofs / Argo CD / ingress / P01-P02 🔒.

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

- `main.tf` cũ **superseded** — không dùng trực tiếp nữa.
- Helm `admin123` **deprecated** — xóa khỏi mọi values/examples, thay bằng secret reference (Key Vault / Sealed Secrets / External Secrets). Không commit password plaintext.
- Mọi `apply` đều yêu cầu approval explícit sau 7A.5.
