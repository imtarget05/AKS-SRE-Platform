# Defense-Prep — 15 Board-Level Questions (Sacombank Production Readiness Review)

**Tên tài liệu:** Defense-Prep — 15 Câu Hỏi Cấp Hội Đồng Quản Trị (Sacombank Production Readiness Review)
**Mục tiêu:** Chuẩn bị trả lời hội đồng quản trị Sacombank trong phiên đánh giá sẵn sàng sản xuất (production readiness review).
**Phạm vi:** kind-local-platform CHỈ. Azure / produzione NÀO cùng trong phạm vi demo này.
**Tình trạng sẵn sàng:** Đây là một engineering baseline, KHÔNG phải chứng nhận Sacombank hay chứng nhận quy định pháp luật. Dự án KHÔNG SẴN SÀNG CHO SẢN XUẤT SACOMBANK theo `docs/QA_PLAN.md` và kết quả phiên làm việc trước; còn 5 cổng P0 đang mở.

> Cảnh báo trung thực: không nên khẳng định sẵn sàng sản xuất nơi dự án ghi rõ "NOT READY". Mỗi câu trả lời dưới đây kèm đường dẫn bằng chứng (file:line hoặc thư mục) trong repo và trạng thái: **Đã giải quyết** / **Cần Sacombank trả lời** / **Còn mở**.

---

## 1. JWT signing key provenance — có khóa ký JWT bị mã hóa cứng không? Bây giờ quản lý như thế nào?

**Câu hỏi:** Có khóa ký JWT được viết cứng (hardcoded) trong mã nguồn không? Sau khi xử lý, khóa được quản lý như thế nào và nào môi trường nào được phép thiếu nó?

**Trả lời:** Không còn khóa cứng. `QUANLYKHO_JWT_KEY` phải được cung cấp qua biến môi trường; thiếu sẽ ném `PermissionError` và agent-hub không bao giờ sở hữu khóa ký JWT được mã hóa cứng.

**Đường dẫn bằng chứng:** `apps/agent-hub/adapters/quan_adapter.py:26-37` — `self.signing_key = signing_key or os.getenv("QUANLYKHO_JWT_KEY")`; `raise PermissionError("QUANLYKHO_JWT_KEY is not configured; agent-hub must never possess a hardcoded JWT signing key")`.

**Trạng thái:** Đã giải quyết (sửa trong phiên này).

---

## 2. Service account passwords — có mật khẩu fallback bị mã hóa cứng không?

**Câu hỏi:** Có tài khoản dịch vụ nào dùng mật khẩu mặc định / fallback được viết cứng không? Sau khi xử lý, mọi mật khẩu dịch vụ phải đến từ đâu?

**Trả lời:** Không còn mật khẩu cứng. `RETAIL_SERVICE_PASSWORD` phải được cung cấp qua biến môi trường; thiếu sẽ ném `PermissionError` và "no hardcoded fallback password allowed".

**Đường dẫn bằng chứng:** `apps/agent-hub/adapters/retail_adapter.py:23-30` — `self.password = os.getenv("RETAIL_SERVICE_PASSWORD")`; `raise PermissionError("RETAIL_SERVICE_PASSWORD is not configured; no hardcoded fallback password allowed")`.

**Trạng thái:** Đã giải quyết (sửa trong phiên này).

---

## 3. Internal endpoints — có tuyến đường thay đổi / sẵn sàng nội bộ chưa xác thực không?

**Câu hỏi:** Có endpoint nội bộ (ví dụ `/internal/readiness`) cho phép đọc hoặc thay đổi trạng thái mà không cần mã thông báo không? Sau khi xử lý, quy tắc fail-closed là gì?

**Trả lời:** Có, nhưng đã được bảo vệ. `/internal/readiness` yêu cầu token nội bộ; trong sản xuất token BẮT BUỘC được cấu hình, không bao giờ hiển thị sẵn sàng chưa xác thực; thất bại đóng (401) khi thiếu hoặc sai token.

**Đường dẫn bằng chứng:** `app/sre-demo-api/src/server.js:114-128` — nhánh `/internal/readiness`, `401 ... internal readiness token not configured`, so sánh `timingSafeEqual`, `401 ... unauthorized`.

**Trạng thái:** Đã giải quyết (sửa trong phiên này).

---

## 4. AKS network — API server công khai? Private cluster? Authorized IP ranges?

**Câu hỏi:** API server AKS có công khai không? Cluster là private cluster không? Authorized IP ranges được cấu hình chưa?

**Trả lời:** Mục tiêu là private cluster (không có API server công khai), nhưng chỉ đối với kind-local-platform; chưa có cụm AKS live để xác minh thực tế. Authorized IP ranges chưa được xác nhận trong demo cục bộ.

**Đường dẫn bằng chứng:** `terraform/aks-foundation/` (IaC AKS foundation); `kubernetes/` (manifests runtime); `docs/QA_PLAN.md` — E2E trên AKS live out-of-scope (cụm AKS đã destroy).

**Trạng thái:** Cần Sacombank trả lời (xác nhận private cluster + authorized IP ranges trên cụm thực).

---

## 5. AKS RBAC — Azure RBAC bật? Tài khoản admin local bị tắt?

**Câu hỏi:** Azure RBAC đã được bật trên AKS chưa? Tài khoản admin local (local admin account) đã bị tắt chưa?

**Trả lời:** Mục tiêu là bật Azure RBAC và tắt tài khoản admin local, nhưng chỉ là kế hoạch hardening cho kind-local-platform; chưa áp dụng / chưa xác minh trên AKS live.

**Đường dẫn bằng chứng:** `terraform/aks-foundation/`; `kubernetes/`; ngữ cảnh phiên làm việc: "private cluster, Azure RBAC, no local admin" là mục tiêu hardening, chưa verify runtime.

**Trạng thái:** Cần Sacombank trả lời (xác nhận trên cụm AKS thực tế).

---

## 6. Node security — SKU, zonas, số nút, container non-root, seccomp, read-only root fs?

**Câu hỏi:** Nút dùng SKU nào? Trải bao nhiêu zona? Ít nhất 2 nút? Container chạy non-root? Seccomp profiles? Read-only root filesystem?

**Trả lời:** Mục tiêu: Standard SKU, zonas 1-2-3, ≥2 nút (chưa xác nhận ngân sách). Các thuộc tính bảo mật nút/container (non-root, seccomp, read-only root fs) chưa được ghi bằng chứng trong demo cục bộ.

**Đường dẫn bằng chứng:** `terraform/aks-foundation/`; `kubernetes/`; ngữ cảnh phiên làm việc: "Standard SKU, zones 1-2-3, ≥2 nodes (pending budget confirmation)".

**Trạng thái:** Cần Sacombank trả lời (xác nhận ngân sách ≥2 nút + zona; bảo mật nút/container chưa có bằng chứng).

---

## 7. NetworkPolicy — default-deny được thi hành? Các namespace nào?

**Câu hỏi:** NetworkPolicy default-deny có được thi hành không? Áp dụng cho namespace nào? Các luồng traffic giữa workload được hạn chế như thế nào?

**Trả lời:** Default-deny đã được định hướng cho agent-hub, langfuse, sre-demo-api, mock-dependency. Các manifest NetworkPolicy cụ thể trong repo chưa được liệt kê chi tiết tại thời điểm ghi tài liệu này; cần xác nhận manifest thực và kiểm tra lại sau khi áp dụng.

**Đường dẫn bằng chứng:** `kubernetes/` (thư mục manifests runtime, bao gồm NetworkPolicy mục tiêu); ngữ cảnh phiên làm việc: "NetworkPolicy default-deny for agent-hub + langfuse + sre-demo-api + mock-dependency".

**Trạng thái:** Còn mở (cần xác nhận manifest NetworkPolicy thực và kiểm tra lại trên cluster).

---

## 8. Secrets management — Key Vault? External Secrets? secretKeyRef ngoài dải?

**Câu hỏi:** Bí mật được lưu ở đâu? Có Azure Key Vault + External Secrets Operator không? Có secretKeyRef được lấy ngoài dải (out-of-band) không?

**Trả lời:** Chưa có. Chưa có bằng chứng Key Vault, External Secrets Operator, hoặc quản lý bí mật tập trung trong repo demo cục bộ; bí mật hiện dùng biến môi trường cục bộ.

**Đường dẫn bằng chứng:** Không có file cấu hình Key Vault / ESO trong repo; `scripts/policy-gate.py` kiểm tra digest placeholder (liên quan supply chain, không phải secrets store). Xem `docs/QA_PLAN.md` — out-of-scope OIDC live login / Azure credentials.

**Trạng thái:** Cần Sacombank trả lời (chọn Key Vault subscription/tenant; quyết định External Secrets hay phân loại LEGACY).

---

## 9. Image supply chain — digest-pinned? Placeholder sha256:0000? SBOM / Trivy / cosign?

**Câu hỏi:** Hình ảnh được ghim theo digest chưa? Có placeholder `@sha256:0000...00000` không? Có SBOM, quét Trivy, ký cosign không?

**Trả lời:** Overlay prod yêu cầu hình ảnh digest-pinned và ký, thay thế mutable tag bằng digest bất biến; `scripts/policy-gate.py` hard-fail khi phát hiện digest placeholder trong `deploy/overlays/prod/kustomization.yaml`. Chưa có bằng chứng SBOM / Trivy / cosign thực tế trong demo cục bộ.

**Đường dẫn bằng chứng:** `deploy/overlays/prod/kustomization.yaml` (P2.9 image sign & digest-pin policy); `scripts/policy-gate.py`; `docs/ACR/image-sign-policy.md` (tham chiếu trong kustomization).

**Trạng thái:** Đã giải quyết (cơ chế chặn placeholder + Digest-pin trong overlay prod); Còn mở (SBOM/Trivy/cosign thực tế chưa có bằng chứng).

---

## 10. Audit trail — log runtime? Bảng audit_events? Ai phê duyệt cái gì?

**Câu hỏi:** Có log runtime có cấu trúc không? Có bảng `audit_events` lưu ai đã làm gì, khi nào, với mã băm trước/sau không? Có thể truy vết phê duyệt không?

**Trả lời:** Có. Có bảng `audit_events` với chỉ mục (actor, scope, thời gian), chặn UPDATE/DELETE qua listener ORM (insert-only), và logger JSON có mã hóa PromQL. Ghi nhận "ai phê duyệt cái gì" qua audit_events.

**Đường dẫn bằng chứng:** `apps/agent-hub/core/storage.py:162-180` (`CREATE TABLE IF NOT EXISTS audit_events` + chỉ mục); `apps/agent-hub/core/storage.py:209` (INSERT audit_events); `apps/agent-hub/core/pii_masker.py` (mã hóa PII trước khi lưu).

**Trạng thái:** Đã giải quyết (cơ chế audit_events tồn tại); Cần Sacombank trả lời (xác nhận quy trình phê duyệt và lưu trữ log dài hạn).

---

## 11. PII handling — masked at persist hay chỉ tại read? Số điện thoại / số tài khoản?

**Câu hỏi:** Thông tin cá nhân (PII) bị che tại thời điểm persist (ghi) hay chỉ khi đọc? Số điện thoại và số tài khoản được che như thế nào?

**Trả lời:** Che tại thời điểm persist. `PIIMasker.sanitize` / `mask_string` áp dụng trước khi lưu vào envelope facts và các trường đề xuất; số điện thoại / số tài khoản được che theo quy tắc PIIMasker.

**Đường dẫn bằng chứng:** `apps/agent-hub/core/pii_masker.py` (lớp `PIIMasker`); `apps/agent-hub/app/main.py:20,24,172,204` (sử dụng PIIMasker và slowapi); `apps/agent-hub/core/storage.py:324` (lưu `PIIMasker.sanitize(envelope.facts)`).

**Trạng thái:** Đã giải quyết (mã hóa PII tại persist); Cần Sacombank trả lời (xác nhận danh sách trường PII và quy tắc che cụ thể cho số điện thoại/số tài khoản).

---

## 12. Data storage — SQLite mã hóa? RPO/RTO? Chiến lược sao lưu?

**Câu hỏi:** Dữ liệu lưu trong SQLite có mã hóa không? Có RPO/RTO xác định không? Chiến lược sao lưu và khôi phục như thế nào?

**Trả lời:** Không. SQLite / lưu tệp cục bộ là chế độ demo; không có mã hóa SQLite (SQLCipher hay mã hóa ổ), không có RPO/RTO, không có chiến lược sao lưu sản xuất.

**Đường dẫn bằng chứng:** `agent_hub.db` (SQLite cục bộ); `docs/QA_PLAN.md` (out-of-scope E2E trên AKS live; không có backup strategy trong demo); ngữ cảnh phiên làm việc: "SQLite/demo mode only; no encrypted PostgreSQL, no RPO/RTO".

**Trạng thái:** Cần Sacombank trả lời (SecEng quyết định mã hóa ổ vs SQLCipher; xác định RPO/RTO và sao lưu).

---

## 13. Disbursement — tích hợp thực Core Banking hay stub?

**Câu hỏi:** Hàm disbursement `execute()` có thực sự chuyển tiền qua Core Banking không hay chỉ là stub?

**Trả lời:** Chỉ là stub. `execute()` là stub không có chuyển tiền thực; không có tích hợp Core Banking.

**Đường dẫn bằng chứng:** Ngữ cảnh phiên làm việc: "Disbursement execute() is a stub; no Core Banking integration"; mã nguồn disbursement cần xác định vị trí chính xác trong repo (không tìm thấy stub trực tiếp tại thời điểm ghi tài liệu này — cần thêm bằng chứng).

**Trạng thái:** Còn mở (cần xác định file stub `execute()` và kế hoạch tích hợp Core Banking).

---

## 14. Identity — IdP OIDC Sacombank đã kết nối? Ánh xạ nhóm-vai trò?

**Câu hỏi:** Issuer / audience / JWKS IdP OIDC của Sacombank đã được kết nối chưa? Ánh xạ nhóm đến vai trò (group-to-role mapping) đã thiết lập chưa? Phê duyệt sản xuất trả về gì nếu chưa kết nối?

**Trả lời:** Chưa kết nối. Issuer / audience / JWKS và ánh xạ nhóm-vai trò chưa được kết nối; phê duyệt sản xuất trả về `PRODUCTION_APPROVAL_NOT_INTEGRATED`.

**Đường dẫn bằng chứng:** Ngữ cảnh phiên làm việc: "Sacombank IdP OIDC issuer/audience/JWKS and group-to-role mapping NOT connected; production approval returns PRODUCTION_APPROVAL_NOT_INTEGRATED"; `docs/QA_PLAN.md` — OIDC live login = NOT_VERIFIED cho đến khi Phase C tạo identity.

**Trạng thái:** Cần Sacombank trả lời (kết nối IdP OIDC + ánh xá nhóm-vai trò; xác định issuer nào gửi token không có aud).

---

## 15. Rollback — Hợp đồng rollback ArgoCD? Autosync tắt trước khi rollback?

**Câu hỏi:** Có hợp đồng rollback ArgoCD (AppProject/Application) không? Autosync được tắt trước khi thực hiện rollback không?

**Trả lời:** ArgoCD được cấu hình qua `gitops/` và `platform/argocd/` (AppProject/Application, version pin). Autosync tắt trước khi rollback chưa có bằng chứng rõ ràng trong demo cục bộ; cần xác nhận quy trình rollback.

**Đường dẫn bằng chứng:** `gitops/` (ArgoCD applications); `platform/argocd/` (VERSION, AppProject/Application); `platform/argocd/applications/quanlykho.yaml` (bootstrap).

**Trạng thái:** Cần Sacombank trả lời (xác nhận hợp đồng rollback và quy tắc tắt autosync trước khi rollback).

---

## Tóm lại — 5 cổng P0 còn mở (theo kết quả phiên làm việc trước)

1. JWT signing key provenance — **Đã giải quyết** (quan_adapter.py), nhưng cần xác nhận không còn khóa cứng ở nơi khác.
2. Service account passwords — **Đã giải quyết** (retail_adapter.py).
3. Internal endpoints auth — **Đã giải quyết** (server.js /internal/readiness).
4. AKS network/RBAC/node — **Cần Sacombank trả lời** (chưa có AKS live).
5. Secrets / Supply chain / Storage / Disbursement / Identity / Rollback — phần đã giải quyết, phần **Cần Sacombank trả lời** / **Còn mở**.

**Lời khuyên:** Không khẳng định sẵn sàng sản xuất cho Sacombank cho đến khi 5 cổng P0 được đóng và các câu hỏi "Cần Sacombank trả lời" được cung cấp đáp án chính thức.
