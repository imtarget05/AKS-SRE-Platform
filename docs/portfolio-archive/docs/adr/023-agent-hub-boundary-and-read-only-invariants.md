# ADR 023: Agent Hub Cross-Repo Architecture, Bounded Scope, and Read-Only Invariants

**Status:** Superseded for action execution by [ADR 024](024-approved-agent-execution.md). The read/evidence controls below remain the baseline. The current Agent Hub code still follows this read-only design; approved execution in ADR 024 is a target architecture, not an implemented capability.

## Context and Problem Statement
Trong hệ thống phân tán gồm 4 hệ thống cốt lõi:
1. `services/retail-finance` (Java 17 / MySQL ledger)
2. `services/opsbridge-flashsale` (.NET 10 / PostgreSQL order & inventory)
3. `services/quanlykho` (Python 3.11 / PostgreSQL inventory & vouchers)
4. `platform/aks-sre-platform` (Argo CD, Envoy Gateway, Kubernetes, Terraform)

Khi xảy ra sự cố (lệch đối soát tài chính, đơn hàng kẹt outbox, chênh lệch kiểm kê kho, hoặc cảnh báo tỷ lệ lỗi tăng đột biến), nhân viên vận hành và SRE phải thủ công thu thập dữ liệu từ nhiều nguồn: database, hàng đợi, logs, alert manager và tài liệu runbook. Quá trình này tốn nhiều thời gian, dễ bỏ sót bối cảnh và tiềm ẩn nguy cơ sai lệch thao tác.

Chúng ta cần một hệ thống điều phối thông minh (**Agent Hub**) giúp tổng hợp chứng cứ và đề xuất phương án điều tra. Tuy nhiên, việc đưa AI vào các hệ thống tài chính, giao dịch và hạ tầng nếu không kiểm soát chặt chẽ sẽ gây ra các rủi ro nghiêm trọng:
- LLM bị ảo giác (hallucination), tự sinh số liệu giao dịch hoặc mã lỗi.
- Quyền ghi (mutation) vô tình được cấp cho Agent, dẫn đến tự ý sửa sổ cái, duyệt xuất kho hay rollback hạ tầng ngoài kiểm soát.
- Lộ lọt dữ liệu giữa các chi nhánh hoặc các đơn vị bán lẻ (cross-scope leakage).

## Decision Drivers
1. **Tuyệt đối an toàn dữ liệu và quyền sở hữu (Data Sovereignty & Safety):** Mỗi service sở hữu trọn vẹn dữ liệu và logic nghiệp vụ của mình. Không một agent nào có quyền bypass tầng nghiệp vụ hay truy vấn raw DB chéo.
2. **Quyền quyết định thuộc về con người (Human-in-the-loop):** Mọi hành động ghi nhận tiền, sửa đơn, trừ tồn, duyệt phiếu kho hay thay đổi hạ tầng cloud/K8s phải do con người có thẩm quyền thực hiện trong UI/CLI chuyên dụng của từng hệ thống.
3. **Chứng cứ có nguồn và kiểm chứng được (Citation & Source Integrity):** Mọi nhận định trong bản phân tích sự cố phải trỏ chính xác về `source_service`, `record_version`, `entity_ref` và `evidence_hash`. Nếu thiếu nguồn, agent bắt buộc phải `abstain` (từ chối suy đoán).
4. **Deterministic Policy Floor:** Các quy tắc kinh doanh cốt lõi (bảo toàn tiền tệ, tồn kho không âm, maker != checker, sàn rủi ro) được thực thi bằng mã nguồn kiểm thử chặt chẽ (deterministic code), không phụ thuộc vào LLM.
5. **Quy tắc 2 thành phần active:** Mỗi giai đoạn phát triển chỉ kích hoạt tối đa Agent Hub và một domain service / platform duy nhất.

## Considered Options
1. **Option 1: Tích hợp Agent phân tán trong từng Repo riêng biệt.**
   - *Ưu điểm:* Độc lập mã nguồn.
   - *Nhược điểm:* Phân tán logic quản lý LLM, trùng lặp công sức xây dựng observability (Langfuse, tracing), không có khả năng tương quan sự cố chéo repo (cross-repo incident correlation giữa AKS alert và OpsBridge queue).
2. **Option 2: Agent Hub toàn quyền đọc/ghi vào Database của cả 4 hệ thống.**
   - *Ưu điểm:* Triển khai nhanh, linh hoạt.
   - *Nhược điểm:* Phá vỡ Clean Architecture, rủi ro bảo mật P0, vi phạm nguyên tắc kiểm soát quyền chi nhánh/outlet, nguy cơ race condition và tham nhũng dữ liệu ledger.
3. **Option 3 (ĐƯỢC CHỌN): Agent Hub tập trung với Read Adapters có phạm vi và Verifier Deterministic.**
   - Đặt Agent Hub trong monorepo tại `services/agent-hub/`.
   - Hub chỉ sở hữu DB riêng cho `runs` và `evidence`.
   - Hub chỉ tương tác với các service qua các REST Read Endpoints được allowlist.
   - Domain service luôn xác thực lại `scope_id` (outlet_id, branch_id) của người dùng/service caller.
   - Kết hợp Deterministic Invariant Verifier trước khi chuyển thông tin cho LLM tổng hợp.

## Decision Outcome
Chọn **Option 3**.

### Các Bất Biến Bắt Buộc (Strict Invariants)
1. **0 Write Tools:** Agent Hub không đăng ký bất kỳ tool nào có hành động mutation (`POST /ledger`, `POST /approve`, `POST /requeue`, `DELETE`, `kubectl apply`).
2. **Read-Only Scope Enforcement:** Mỗi yêu cầu đọc dữ liệu bắt buộc đi kèm `user_token` và `scope_id`. Nếu truy cập ngoài phạm vi được cấp quyền, domain adapter trả về `403 Forbidden` / `404 Not Found`.
3. **Evidence Envelope Immutability:** Mọi thông tin thu thập được đóng gói trong `EvidenceEnvelope` kèm SHA-256 hash và thời điểm hết hạn `expires_at`.
4. **Abstain Policy:** Nếu model gặp dữ liệu xung đột, tool timeout, hoặc không tìm thấy nguồn gốc xác thực, đề xuất phải gắn cờ `abstained: true` và nêu rõ trong danh sách `unknowns`.
5. **No Direct Execution of Runbooks:** Các bước gợi ý trong đề xuất chỉ ở dạng văn bản chỉ dẫn (`suggested_read_only_checks`), tuyệt đối không tự động sinh hay thực thi shell script.

## Positive Consequences
- Đảm bảo tuân thủ tiêu chuẩn kỹ thuật cấp Senior: Phân tách rõ ràng giữa phân tích (analysis) và quyết định (decision).
- Giảm thời gian điều tra sự cố mà không tạo thêm rủi ro an toàn vận hành.
- Dễ dàng kiểm thử độc lập bằng Mock / Testcontainers mà không ảnh hưởng dữ liệu sản xuất.

## Negative Consequences & Mitigations
- *Độ trễ do nhiều bước verifier:* Giảm thiểu bằng cách thực thi song song các Read Adapter và caching cục bộ ngắn hạn theo `entity_ref` và `record_version`.
- *Chi phí gọi LLM:* Chỉ kích hoạt synthesis khi các deterministic verifier xác nhận có bất thường; các case đơn giản được xử lý hoàn toàn bằng rule-based engine.
