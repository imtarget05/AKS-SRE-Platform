# Câu hỏi mở cần Sacombank trả lời (Sacombank Open Questions)

**Tên tài liệu:** Câu hỏi mở cần Sacombank trả lời
**Mục tiêu:** Danh sách 6 câu hỏi còn thiếu đáp án từ bên Sacombank theo kế hoạch dự án, liên quan trực tiếp đến sẵn sàng sản xuất.
**Phạm vi:** kind-local-platform CHỈ. Azure / produzione NÀO cùng trong phạm vi demo này.
**Liên quan:** Các câu hỏi này được tham chiếu trong `docs/defense/defense-prep.md` với trạng thái **Cần Sacombank trả lời**.

---

## 1. Budget cluster — đã xác nhận ≥2 nút + zone

**Câu hỏi:** Ngân sách cluster đã xác nhận chưa? Có thể cung cấp ít nhất 2 nút trải zona 1-2-3 không?

**Tại sao cần đáp án:** Mục tiêu hardening AKS là Standard SKU, zones 1-2-3 và tối thiểu 2 nodes. Xác nhận budget là prerequisite để giữ cấu hình multi-node / multi-zone cho target cluster.

**Đường dẫn bằng chứng:** `terraform/aks-foundation/`; `terraform/modules/aks_cluster/`; `kubernetes/`.

**Trạng thái:** Đã xác nhận — target AKS dùng tối thiểu 2 system nodes trên zones 1-2-3. Terraform vẫn chỉ được verify tĩnh; chưa có cloud apply.

---

## 2. Key Vault subscription/tenant?

**Câu hỏi:** Azure Key Vault dùng subscription và tenant nào? Có External Secrets Operator không, hay bí mật quản lý như thế nào?

**Tại sao cần đáp án:** Chưa có bằng chứng Key Vault / ESO trong repo demo cục bộ; bí mật hiện dùng biến môi trường cục bộ. Cần Sacombank xác định subscription/tenant và mô hình quản lý bí mật sản xuất.

**Đường dẫn bằng chứng:** Không có file cấu hình Key Vault / ESO trong repo; `scripts/policy-gate.py` (chỉ liên quan supply chain digest, không phải secrets store); `docs/QA_PLAN.md` — out-of-scope Azure credentials / OIDC live login.

**Trạng thái:** Cần Sacombank trả lời.

---

## 3. SQLite encryption: volume encryption vs SQLCipher (SecEng quyết định)?

**Câu hỏi:** Dữ liệu SQLite được mã hóa thế nào — mã hóa ổ (volume encryption) hay SQLCipher? Ai quyết định (SecEng)?

**Tại sao cần đáp án:** SQLite / lưu tệp cục bộ là chế độ demo; không có mã hóa SQLite, không có RPO/RTO, không có chiến lược sao lưu sản xuất. Cần SecEng đưa ra quyết định mã hóa trước khi coi là sẵn sàng sản xuất.

**Đường dẫn bằng chứng:** `agent_hub.db` (SQLite cục bộ); `docs/QA_PLAN.md` (không có backup strategy trong demo); ngữ cảnh phiên làm việc: "SQLite/demo mode only; no encrypted PostgreSQL, no RPO/RTO".

**Trạng thái:** Cần Sacombank trả lời (quyết định của SecEng).

---

## 4. Console ingress — cùng domain với agent-hub hay edge auth riêng?

**Câu hỏi:** Ingress của console dùng cùng domain với agent-hub hay có edge auth riêng?

**Tại sao cần đáp án:** Ảnh hưởng đến mô hình xác thực và điều hướng truy cập console so với agent-hub trên cùng nền tảng cục bộ.

**Đường dẫn bằng chứng:** `apps/sre-console/index.html` (bảo mật client-side: không hardcoded secret); `kubernetes/` (manifests ingress/runtime); `docs/QA_PLAN.md` — out-of-scope E2E trên AKS live.

**Trạng thái:** Cần Sacombank trả lời.

---

## 5. Auth aud mandatory: có issuer nào gửi token không có aud không?

**Câu hỏi:** Trong mô hình xác thực, có issuing authority (issuer) nào gửi token không có claim `aud` không? Nếu có, quy tắc bắt buộc aud được áp dụng như thế nào?

**Tại sao cần đáp án:** Cần xác nhận tất cả issuer gửi token đều có `aud`, hoặc quy xử lý cho token thiếu `aud`, trước khi bật quy tắc auth aud bắt buộc.

**Đường dẫn bằng chứng:** `docs/QA_PLAN.md` — OIDC live login = NOT_VERIFIED cho đến khi Phase C tạo identity; ngữ cảnh phiên làm việc: "Sacombank IdP OIDC issuer/audience/JWKS ... NOT connected".

**Trạng thái:** Cần Sacombank trả lời.

---

## 6. KEDA/rabbitmq secret — ESO thay thế hay phân loại LEGACY?

**Câu hỏi:** Bí mật KEDA / rabbitmq được thay thế bằng External Secrets Operator (ESO) hay được phân loại là LEGACY (ngừng dùng)?

**Tại sao cần đáp án:** KEDA install bị tắt theo mặc định, chỉ bật với `INSTALL_KEDA=1` sau workload/identity review. Bí mật KEDA/rabbitmq cần quyết định thay thế bằng ESO hay phân loại LEGACY.

**Đường dẫn bằng chứng:** `kubernetes/keda-autoscaler.yaml`; `kubernetes/keda-trigger-auth.yaml`; ngữ cảnh phiên làm việc: "KEDA install is disabled by default; enable only with INSTALL_KEDA=1 after workload/identity review."

**Trạng thái:** Cần Sacombank trả lời.

---

## Tóm tắt trạng thái

Câu hỏi #1 đã có xác nhận về budget/zone prerequisite. Năm câu hỏi #2-#6 vẫn có trạng thái **Cần Sacombank trả lời** và không được coi là đã giải quyết trong engineering baseline hiện tại. Không khẳng định sẵn sàng sản xuất cho Sacombank cho đến khi các câu hỏi còn lại có đáp án chính thức và có bằng chứng live phù hợp.
