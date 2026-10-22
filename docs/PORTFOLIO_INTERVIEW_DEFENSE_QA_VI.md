# Tài liệu Phòng Thủ Phỏng Vấn Kỹ Thuật (Portfolio Defense Q&A)

> **Mục tiêu:** Cung cấp bộ câu hỏi - câu trả lời chi tiết, có số liệu thực chứng (evidence-first) và bảo vệ kiến trúc (architectural defense) dành cho ứng viên Senior Backend / Cloud / Platform / AI Systems Engineer.  
> **Căn cứ bằng chứng:** `gap-register.md`, `canonical-repository-decisions.md`, `portfolio-audit.md`, `reusable-assets-register.md`, và 25+ ADRs trong toàn bộ hệ thống.

---

## Mục lục
1. [Kiến trúc Tổng thể & Ranh giới Hệ thống (System Architecture & Bounded Contexts)](#1-kiến-trúc-tổng-thể--ranh-giới-hệ-thống)
2. [OpsBridge & FlashSale: Concurrency, Zero-Oversell & Outbox Pattern](#2-opsbridge--flashsale-concurrency-zero-oversell--outbox-pattern)
3. [Retail Finance: Idempotency & Optimistic Concurrency Control](#3-retail-finance-idempotency--optimistic-concurrency-control)
4. [QuanLyKho: Maker-Checker, Dual-Entry Simulation & MLOps Ingestion](#4-quanlykho-maker-checker-dual-entry-simulation--mlops-ingestion)
5. [AKS-SRE-Platform: Độ tin cậy hạ tầng, SLI/SLO & GitOps](#5-aks-sre-platform-độ-tin-cậy-hạ-tầng-slislo--gitops)
6. [SmartDocumentChatbot: Corrective RAG (CRAG), LangGraph & HITL](#6-smartdocumentchatbot-corrective-rag-crag-langgraph--hitl)
7. [Câu hỏi Phản biện Kiến trúc: Tại sao KHÔNG đưa AI vào luồng đặt hàng (Hot Path)?](#7-câu-hỏi-phản-biện-kiến-trúc-tại-sao-không-đưa-ai-vào-luồng-đặt-hàng-hot-path)

---

## 1. Kiến trúc Tổng thể & Ranh giới Hệ thống

### Q1: Monorepo hay Multi-repo? Tại sao bạn lại tách 4 repositories riêng biệt thay vì gom thành một Monolith hoặc chia nhỏ thành 20 microservices?
**Trả lời:**
- **Không gom thành một cơ sở dữ liệu dùng chung (Decision C1 - C4):** Mỗi hệ thống đại diện cho một **Bounded Context** độc lập với trách nhiệm và tốc độ thay đổi khác nhau:
  - `OpsBridge` (.NET 10): Đảm bảo thông lượng cao, không bán vượt (zero-oversell) và đối soát vận hành (3-way reconciliation).
  - `retail-finance-core-platform` (Java 17 Spring Boot): Lõi kế toán giao dịch (idempotent financial ledger) với chuẩn mực bất biến của số dư tài khoản.
  - `QuanLyKho` (Python FastAPI): Quản lý tồn kho thực tế của chuỗi trà sữa (theo lô/hạn dùng) kết hợp quy trình phê duyệt kép (Maker-Checker).
  - `SmartDocumentChatbot` (Python/FastAPI + Java + React): Nền tảng Enterprise Corrective RAG (CRAG) và LangGraph agents.
  - `AKS-SRE-Platform` (Terraform, Argo CD, Kubernetes): Nền tảng hạ tầng dùng chung, áp dụng chuẩn SRE.
- **Quy tắc bất biến:** *Không bao giờ chia sẻ database writes giữa các bounded contexts.* Mọi tích hợp liên repo nếu có đều thông qua REST API có phiên bản hoặc hàng đợi sự kiện (event contracts), đi kèm regression test gate.
- **Tránh bẫy Microservices sớm:** Bắt đầu bằng **Modular Monolith** có cấu trúc Clean Architecture chuẩn (`Domain <- Application <- Infrastructure <- Presentation`) được kiểm soát tự động bằng unit tests (`ArchitectureTests.cs`), giúp tiết kiệm chi phí mạng, độ phức tạp của phân tán (distributed transactions) mà vẫn bảo đảm phân tách trách nhiệm.

---

## 2. OpsBridge & FlashSale: Concurrency, Zero-Oversell & Outbox Pattern

### Q2: Trong sự kiện Flash Sale (50 người tranh mua 10 sản phẩm trong <100ms), bạn giải quyết bài toán chống bán âm (Zero-Oversell) như thế nào?
**Trả lời:**
- **Giải pháp:** Sử dụng mô hình đặt chỗ đa tầng (**Multi-tier Reservation**):
  1. **Tầng lọc nhanh (Fast-fail Filter) với Redis Lua Script:**
     - Script Lua thực hiện nguyên tử (atomic): Kiểm tra khóa `reservation:{productId}` xem buyer đã mua chưa (idempotency), đọc số dư hiện tại trong hash `stock:{productId}`, nếu `stock >= qty` thì trừ tồn kho và ghi lại mã đặt chỗ.
     - Toàn bộ thao tác chỉ mất dưới 1ms trong bộ nhớ đơn luồng của Redis. 40 khách hàng đến sau nhận ngay phản hồi `409 Conflict` (hoặc `422 Sold Out`) mà không chạm vào PostgreSQL, bảo vệ DB không bị sập vì nghẽn kết nối.
  2. **Tầng lưu trữ bền vững (Durable Persistence) với PostgreSQL:**
     - Đơn hàng hợp lệ được ghi vào database kèm theo sự kiện `order.created` trong cùng **một transaction duy nhất** bằng **Transactional Outbox Pattern**.
- **Số liệu kiểm chứng thực tế (Harness Test):**
  - Chạy `load-tests/concurrency/oversell_demo.py` với 50 concurrent buyers tranh mua stock = 10:
  - Kết quả: **Đúng 10 đơn được chấp nhận**, **40 yêu cầu bị từ chối với HTTP 409**, số lượng tồn kho cuối cùng trong DB chính xác bằng 0, không có sai lệch âm.

### Q3: Tại sao bạn không dùng Distributed Lock (Redlock) hoặc `SELECT ... FOR UPDATE` trong Database?
**Trả lời:**
- `SELECT ... FOR UPDATE` (Pessimistic Locking) trong RDBMS: Khi 500–1000 kết nối cùng tranh chấp một hàng (hot row) trong bảng `stock`, hàng loạt connection của PostgreSQL sẽ rơi vào trạng thái lock wait, làm cạn kiệt connection pool, tăng CPU wait và dẫn đến sập toàn bộ dịch vụ đặt hàng.
- **Redlock (Distributed Lock trên Redis cluster):** Gây overhead lớn do phải gửi request lock/unlock qua mạng trước và sau mỗi nghiệp vụ. Trong bài toán flash sale, ta chỉ cần trừ số lượng nguyên tử chứ không cần chiếm quyền khóa toàn diện. Một script **Redis Lua CAS (Check-And-Set)** thực thi nguyên tử trên single thread của Redis giải quyết triệt để vấn đề mà không cần distributed lock.
- **Nguyên tắc cốt lõi:** Redis chỉ là *bộ lọc loại trừ nhanh (rate-limiting filter)*, **PostgreSQL mới là Source of Truth**. Khi Redis sập, hệ thống chuyển sang chế độ Fail-Closed hoặc Sync Fallback kiểm tra trực tiếp DB.

### Q4: Trình bày cơ chế Transactional Outbox Pattern và cách hệ thống xử lý khi Message Broker gặp sự cố?
**Trả lời:**
- **Vấn đề (Dual-write problem):** Nếu ghi đơn hàng vào DB thành công nhưng publish message sang RabbitMQ bị lỗi mạng, hệ thống mất thông tin xử lý đơn hàng. Ngược lại, nếu gửi message trước nhưng DB rollback, công nhân xử lý đơn hàng ảo.
- **Giải pháp Outbox Pattern (ADR-015/019):**
  - Khi lưu `Order`, bảng `OutboxEvents` được ghi đồng thời trong cùng một database transaction (`AppDbContext.SaveChangesAsync()`).
  - Một tiến trình nền (`OrderProcessorHost` / Outbox Dispatcher) đọc các message chưa gửi từ bảng `OutboxEvents`, gửi đến RabbitMQ kèm cờ **Publisher Confirms**.
  - Chỉ khi RabbitMQ trả lời `ACK`, bản ghi outbox mới được đánh dấu `ProcessedAt = UTCNow`.
- **At-least-once & Idempotency:** Vì là cơ chế *ít nhất một lần (at-least-once)*, message có thể bị gửi lặp lại khi mạng chập chờn. Consumer nhận message luôn dựa vào `IdempotencyKey` hoặc `OrderId` để loại bỏ xử lý trùng lặp.

---

## 3. Retail Finance: Idempotency & Optimistic Concurrency Control

### Q5: Trong `retail-finance-core-platform`, bạn bảo đảm tính Idempotent của giao dịch chuyển tiền như thế nào khi client gửi lặp lại (retry)?
**Trả lời:**
- **Thiết kế Idempotency Key 2 lớp:**
  1. **Lớp Database:** Cột `idempotency_key` được đặt ràng buộc `UNIQUE INDEX uk_txn_idempotency` trên bảng `transactions`.
  2. **Lớp Ứng dụng (Spring Boot Service):**
     - Khi nhận request có `idempotencyKey`: Trước tiên tra cứu `transactionRepository.findByIdempotencyKey(key)`. Nếu đã tồn tại bản ghi, trả lại ngay kết quả của giao dịch trước đó (HTTP 200 OK) mà không trừ tiền lần hai.
     - **Race Condition Handling:** Trong tình huống 2 request trùng key đến đồng thời và vượt qua bước kiểm tra đầu tiên, database transaction nào hoàn tất trước sẽ ghi thành công. Giao dịch đến sau vi phạm unique constraint và ném ngoại lệ `DataIntegrityViolationException`. Lớp `GlobalExceptionHandler` bắt ngoại lệ này, tự động query lại hàng đã thắng cuộc (winner row) và trả về kết quả hợp lệ cho client.
- **Khoản tiền (Money representation):** Dùng kiểu dữ liệu `BIGINT` (lưu đơn vị tiền tệ nhỏ nhất là VND hoặc cents), tuyệt đối không dùng `FLOAT/DOUBLE` để tránh lỗi sai số làm tròn dấu phẩy động (IEEE 754).

### Q6: Optimistic Locking với `@Version` hoạt động như thế nào trong bài toán trừ số dư tài khoản?
**Trả lời:**
- Entity `Account` có trường `@Version private Long version;` và DB constraint `CHECK (balance >= 0)`.
- Khi Hibernate update tài khoản: Sinh ra câu lệnh `UPDATE accounts SET balance = ?, version = version + 1 WHERE id = ? AND version = ?`.
- Nếu hai giao dịch cùng đọc version = 5: Giao dịch A commit trước tăng version lên 6. Khi giao dịch B thực thi lệnh UPDATE, số dòng bị ảnh hưởng là 0, JPA ném `OptimisticLockingFailureException`.
- Hệ thống catch ngoại lệ và từ chối giao dịch B hoặc retry an toàn, ngăn chặn hoàn toàn lỗi **Lost Updates** mà không cần khóa cứng bảng dữ liệu.

---

## 4. QuanLyKho: Maker-Checker, Dual-Entry Simulation & MLOps Ingestion

### Q7: Quy trình Maker-Checker (Kiểm soát 4 mắt) và Dual-Entry Ledger trong QuanLyKho hoạt động ra sao?
**Trả lời:**
- **Maker-Checker:**
  - Nhân viên ca (Maker) tạo phiếu yêu cầu xuất/nhập/điều chỉnh kho (`StockRequest`). Phiếu ở trạng thái `PENDING`.
  - Kiểm soát viên (Checker) phải là một người dùng khác (RBAC phân tách quyền rõ rệt; Maker không được tự duyệt phiếu của chính mình).
  - Phê duyệt yêu cầu chữ ký PIN, ghi nhận vết kiểm toán bằng mã băm SHA-256 (`audit_stamps`).
- **Mô phỏng Kế toán kép (Dual-Entry Simulation):**
  - Mọi dịch chuyển tồn kho đều sinh ra bút toán nợ - có tương ứng (Debit/Credit), ví dụ: Ghi nợ tài khoản Kho Hàng Hóa - Ghi có tài khoản Giá Vốn hoặc Phải Trả Nhà Cung Cấp. Tổng Nợ luôn phải cân bằng với Tổng Có (`Sum(Debit) == Sum(Credit)`).
- **Ranh giới sản phẩm:** Ứng dụng tập trung vào kho trà sữa thực tế; phần tài chính là mô phỏng vận hành nội bộ (không phải hệ thống Core Banking thật, không kết nối thanh toán ngân hàng trực tiếp).

### Q8: MLOps Pipeline và AI Risk-Scoring trong QuanLyKho được thiết kế như thế nào?
**Trả lời:**
- **MLOps với Apache Airflow 3.3.2 & MLflow:**
  - 3 DAGs tại `infra/airflow/dags/` (`inventory_ingestion.py`, `expense_ingestion.py`, `supplier_ingestion.py`): Đọc dữ liệu thô -> Xác thực schema -> Nạp vào bảng Staging (idempotent) -> Chạy huấn luyện mô hình dự báo nhu cầu (`demand forecasting`).
  - Kết quả và metrics được ghi vào **MLflow Tracking Server**; mô hình đạt chuẩn được tự động promote lên Production trong **MLflow Model Registry** (Đã kiểm chứng E2E ngày 2026-10-20 trong tài liệu `docs/mlops/airflow-ingest-evidence-2026-10-20.md`).
- **AI Risk-Scoring Advisor (`ai.py`):**
  - Đóng vai trò cố vấn chấm điểm rủi ro cho phiếu điều chỉnh kho hoặc chi quỹ, trả về định dạng JSON nghiêm ngặt (`risk_level`, `risk_score`, `flagged_rules`).
  - **Graceful Degradation (Fail-safe):** Khi LLM service không khả dụng hoặc trả về sai schema, hệ thống tự động fallback về hàm Heuristic rule-based (`assess_request_heuristic`), đảm bảo luồng duyệt kho của cửa hàng không bao giờ bị gián đoạn.

---

## 5. AKS-SRE-Platform: Độ tin cậy hạ tầng, SLI/SLO & GitOps

### Q9: Trình bày quy trình kiểm thử PodDisruptionBudget (PDB) Drain Drill và Disaster Recovery Drill trên Kubernetes?
**Trả lời:**
- **PDB Drain Drill (Bằng chứng `pdb-drain-drill-PASS.md`):**
  - Thiết lập `PodDisruptionBudget` với `minAvailable: 1` cho workload có 2 replicas.
  - Chạy script mô phỏng bảo trì node: `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`.
  - Kết quả: Kubernetes di chuyển tuần tự từng Pod sang node khác. Một Pod luôn giữ trạng thái `Running` để tiếp nhận traffic, tỉ lệ lỗi HTTP 5xx đo được trong suốt quá trình drain là **0%**.
- **Disaster Recovery Rehearsal (Bằng chứng `disaster-recovery-drill-PASS.md`):**
  - Kịch bản: Mô phỏng database bị xóa sổ hoàn toàn (`DROP DATABASE bankops`).
  - Thực thi: Script khôi phục tự động từ snapshot gần nhất, chạy Alembic migration đối soát, và kiểm tra tính toàn vẹn của số dư và bảng Idempotency Ledger.
  - Toàn bộ thời gian phục hồi (RTO) dưới 90 giây; dữ liệu không bị thất thoát (RPO = 0 đối với các giao dịch đã commit snapshot).

### Q10: Sự khác biệt giữa môi trường `kind` và `Azure AKS` trong portfolio của bạn là gì?
**Trả lời:**
- **Minh bạch môi trường:**
  - Nhãn `PRE_AZURE_DRY_RUN`: Áp dụng cho các bài test chạy trên cụm local `kind` (Argo CD, Envoy Gateway, NetworkPolicy, PDB, Prometheus alerts).
  - Nhãn `Azure`: Áp dụng cho hạ tầng đã apply Terraform thật trên Azure (đợt kiểm chứng 2026-09-21 và 2026-10-21).
  - Cụm Azure AKS sau khi kiểm chứng đã được chạy script `azure-teardown` để xóa sạch tài nguyên nhằm triệt tiêu chi phí đám mây (Cost-Safe Policy: \$0 Azure ongoing cost). Không bao giờ mạo nhận kết quả test trên `kind` là bằng chứng runtime trên Azure.

---

## 6. SmartDocumentChatbot: Corrective RAG (CRAG), LangGraph & HITL

### Q11: Kiến trúc Corrective RAG (CRAG) 5 lớp giải quyết bài toán Hallucination (Ảo giác) như thế nào?
**Trả lời:**
- **5 Lớp Kiểm định (Verification Pipeline):**
  1. **Hybrid Retrieval (RRF):** Kết hợp Dense Vector Search (Qdrant Cosine) + Sparse Keyword Search (BM25), dung hợp điểm bằng Reciprocal Rank Fusion (RRF), bảo đảm độ phủ ngữ nghĩa lẫn từ khóa chính xác.
  2. **Relevance Grading:** Đánh giá tính liên quan của từng chunk tài liệu được trả về. Loại bỏ các đoạn nhiễu.
  3. **Knowledge Refinement:** Trích xuất các ý chính yếu từ các chunk đạt chuẩn.
  4. **Hallucination Check:** Kiểm tra câu trả lời sinh ra có nằm trong phạm vi tài nguyên trích xuất hay không.
  5. **Answer Grading & Abstention:** Nếu ngữ cảnh không đủ bằng chứng, hệ thống **từ chối trả lời một cách trung thực (Abstain)** thay vì tự bịa câu trả lời.
- **Local-First LLM Routing:** Ưu tiên gọi mô hình Ollama chạy local (kiểm tra qua TTL health cache). Chỉ fallback sang Cloudflare Workers AI khi local down; không fallback giữa chừng (fail-fast, fail-clean).
- **Human-in-the-Loop (HITL) qua LangGraph:** Các hành động có tác động phụ (ghi dữ liệu, phát tán thông báo) buộc phải đi qua trạng thái `approval_request` chờ người kiểm duyệt xác nhận trước khi agent thực thi.

---

## 7. Câu hỏi Phản biện Kiến trúc: Tại sao KHÔNG đưa AI vào luồng đặt hàng (Hot Path)?

### Q12: "Tại sao bạn không dùng một Agentic AI để nhận đơn hàng và tự động quyết định mua hàng trong OpsBridge?"
**Trả lời (Phản biện dứt khoát của một Senior Engineer):**
- **Đây là một Anti-Pattern nghiêm trọng trong kỹ thuật phần mềm phân tán:**
  1. **Độ trễ (Latency):** Flash sale yêu cầu phản hồi trong **50–100ms** để giữ chân khách hàng và tránh giữ kết nối DB. Một lệnh gọi LLM mất từ **800ms đến 3000ms**, làm tắc nghẽn toàn bộ pipeline tiếp nhận.
  2. **Tính tất định (Determinism):** Đặt hàng flash sale là bài toán đếm và trừ số nguyên tử (ACID transaction). Số lượng tồn kho là 10, nếu cho 11 người mua thì là lỗi hệ thống. LLM là mô hình xác suất (probabilistic), không thể cam kết bất biến số học nguyên tử.
  3. **Chi phí và Khả năng chịu tải:** 10.000 requests/giây gửi vào LLM sẽ làm cạn hạn mức token (Rate Limits), chi phí API khổng lồ và hệ thống sập ngay lập tức.
- **Đưa AI vào đâu là đúng đắn?**
  - **AIOps (Ngoài luồng giao dịch):** Phân tích log bất thường, tự động phát hiện node Kubernetes quá tải, gợi ý runbook xử lý sự cố cho kỹ sư trực SRE.
  - **Trợ lý tư vấn sau giao dịch:** Phân tích giỏ hàng, gợi ý bổ sung kho (Reorder Recommendation trong OpsBridge/QuanLyKho) trên dữ liệu đã commit vào PostgreSQL.
  - **Trợ lý RAG & Tri thức:** Tra cứu tài liệu chính sách, hợp đồng và hỗ trợ khách hàng như trong `SmartDocumentChatbot`.

---

## Bảng tra cứu Bằng chứng Thực tế (Evidence Quick Reference)

| Khẳng định năng lực | Vị trí File Bằng chứng trong Repo | Kết quả kiểm chứng |
|---|---|---|
| Zero-Oversell Concurrency | `OpsBridge/load-tests/concurrency/oversell_demo.py` | 50 buyers / 10 units -> 10 accepted, 40 × 409, stock 0 |
| Clean Architecture Enforced | `OpsBridge/tests/UnitTests/ArchitectureTests.cs` | Build FAIL nếu Domain phụ thuộc Infra/Framework |
| Zero Downtime Maintenance | `AKS-SRE-Platform/docs/evidence/pdb-drain-drill-PASS.md` | PDB drain giữ 1 pod alive, 0% 5xx errors |
| Airflow E2E Ingestion + ML | `QuanLyKho/docs/mlops/airflow-ingest-evidence-2026-10-20.md` | Airflow 3.3.2 chạy 3 DAGs thật, MLflow logging & model promote |
| CRAG 5-Layer Hallucination Guard | `SmartDocumentChatbot/eval/portfolio_demo/` | 395/395 backend tests pass, hybrid search RRF, honest abstention |
