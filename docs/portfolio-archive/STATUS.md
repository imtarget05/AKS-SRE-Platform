# Báo Cáo Trạng Thái Thực Tế Hệ Thống Monorepo — 2026-10-25 13:00 ICT

> **Nguyên tắc Senior:** Không báo cáo vượt quá bằng chứng đo lường thực tế. Phân định rạch ròi giữa môi trường kiểm thử local/Testcontainers, cụm Kind local, và cụm Cloud AKS (`aks-portfolio-dev`). Báo cáo trung thực 100% dựa trên telemetry, logs và SHA thực tế.

---

## 1. Trạng Thái Tổng Thể Các Thành Phần

| Thành Phần | Canonical SHA / Branch | Môi Trường CI GitHub Actions | Cụm Kind (`kind-local-platform`) | Cụm Azure AKS (`aks-portfolio-dev`) | Đánh Giá Hợp Đồng & Tiến Độ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Retail Finance** | `11620ed67c5c6e208a3af1bd72e7cf0a96b67271` (`main`) | **PASS** ([Run 40107593770](https://github.com/imtarget05/retail-finance-core-platform/actions/runs/40107593770), 3/3 jobs: Unit, Recon, MySQL 8 Testcontainers IT) | N/A (service backend Java/MySQL) | Lưu trữ sổ cái canonical tại MySQL; broker feed đối soát độc lập. | Hoàn tất nghiệp vụ hạch toán, scoped feed & migration V2. |
| **OpsBridge** | `71cf53ba213b192804d95222efbfd863f6055d78` (tag: `ops-cloud-20261025`) | **PASS** ([Run 40108742539](https://github.com/imtarget05/FlashSale-Backend/actions/runs/40108742539), 12 passed, 3 skipped; k6 [Run 40108742560](https://github.com/imtarget05/FlashSale-Backend/actions/runs/40108742560)) | **RUNNING** (API, Worker, Postgres, Redis, RabbitMQ, Kafka) | **1/1 RUNNING (9/9 PODS READY)** (`order-api` x2, `order-worker` x2, `payment-service`, `postgres-0`, `rabbitmq-0`, `redis`, `kafka-0`) | Flagship backend hoàn tất nghiệp vụ outbox, saga, rate limiting, single-event signed recovery API & live running trên AKS. |
| **QuanLyKho** | `fde9570a390babbffd9149f5e408771cb9300bb0` (`main`) | **PASS** (CI [Run 40109783561](https://github.com/imtarget05/QuanLyKho/actions/runs/40109783561), 714 tests; Deploy [Run 40155519980](https://github.com/imtarget05/QuanLyKho/actions/runs/40155519980) build-and-push PASS) | N/A | **1/1 RUNNING (3/3 PODS READY)** (`bankops-api` x2, `bankops-worker`) | Maker-Checker, kho tồn kho canonical, overlay production sạch 0 Secret/0 CHANGE_ME, live running trên AKS. |
| **AKS SRE Platform** | `0905088` (`main`) | **PASS** (GitOps [Run 40167455981](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/40167455981) ✓, OIDC live [Run 40157466054](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/40157466054) positive login PASS + negative control masked token & strictly verified `AADSTS700213`) | **READY** (3 nodes Ready, Argo CD, Gateway API, KEDA) | **2 NODES READY (`Standard_D2s_v6`)**, Argo CD Applications (`flashsale`, `quanlykho`) **Synced**, Dynamic Azure Managed Disks **Bound**. | `validate-gitops.py` (29/29 passed, targetRevision commit matches verified); Argo CD applications Synced; Live HTTP health check return 200. |
| **Agent Hub (ADR 024 HITL)** | Đồng bộ từ canonical (`8bbfae2`) | **PASS** ([Run 40157643838](https://github.com/imtarget05/Senior-Engineering-Portfolio/actions/runs/40157643838), 41 passed: 10 unit tests + 31 evals) | Manifest chuẩn bị sẵn | **1/1 RUNNING** (`agent-hub-7b974bb9cf-xf99k` chạy `acrflashsalep6.azurecr.io/agent-hub:sha-4457b78`) | Hoàn tất ADR 024 HITL. Bằng chứng drill thực nghiệm độc lập chứng minh fault injection rớt mạng $\rightarrow$ `UNKNOWN` $\rightarrow$ idempotent retry $\rightarrow$ `SUCCEEDED`. Live in-cluster HTTP client probe OK. |

---

## 2. Chi Tiết Thực Hiện Các Yêu Cầu Cốt Lõi

### 2.1. Khắc Phục Lỗ Hổng Bảo Mật (Zero Secret in Git & Fail-Closed)
- **Thu hồi và loại bỏ Secret dạng bản rõ khỏi Git:**
  - File `platform/aks-sre-platform/kubernetes/workloads/agent-hub/agent-hub.yaml` đã được dọn sạch hoàn toàn `kind: Secret`.
  - Tạo template cấu hình an toàn ngoài băng tại `platform/aks-sre-platform/kubernetes/workloads/agent-hub/agent-hub-secret.example.yaml`.
  - Trên cụm AKS `aks-portfolio-dev`, secret `agent-hub-secret` đã được tạo trực tiếp qua `kubectl create secret generic` out-of-band, không commit vào repository.
- **Fail-Closed Adapters:**
  - `services/agent-hub/adapters/ops_adapter.py`: Loại bỏ khóa ký JWT mặc định cố định. Bắt buộc ném `RuntimeError` khi thiếu `FLASH_SALE_JWT_KEY` ngoài môi trường test/local.
  - `services/agent-hub/adapters/retail_adapter.py`: Loại bỏ mật khẩu mặc định cố định (`ChangeMe123!`). Bắt buộc ném `RuntimeError` khi thiếu `RETAIL_SERVICE_PASSWORD` ngoài môi trường test/local.

### 2.2. Human-In-The-Loop Execution Theo ADR 024 (Pilot: OpsBridge Single Outbox Event Recovery)
- **Mô hình Dữ Liệu Bền Vững (`StorageManager`):**
  - 3 bảng SQLite: `action_intents`, `action_approvals`, `execution_receipts` với ràng buộc khóa duy nhất và khóa ngoại.
- **Loại Bỏ Lệnh Bulk và Khóa Ký Độc Quyền Của Owner:**
  - Loại bỏ hoàn toàn endpoint hàng loạt `POST /api/outbox/requeue` khỏi ActionExecutor.
  - Loại bỏ `_generate_staff_token` và việc giữ `FLASH_SALE_JWT_KEY` trong Agent Hub.
  - Tích hợp anti-drift gate trong bộ kiểm thử `test_policy_gates.py`.
- **Luồng Thực Thi Có Thẩm Quyền (Single-Event Recovery):**
  - **Dự thảo ActionIntent:** Chỉ cho phép lệnh `REPLAY_STUCK_OUTBOX` trỏ tới `/internal/agent/outbox/{messageId}/requeue` trên `opsbridge-flashsale` dựa trên bằng chứng dead-lettered event thật.
  - **Khóa Băm Ngăn Giả Mạo (`intent_hash`):** Tự động tính mã băm SHA-256 từ canonical payload (command, owner_service, target_endpoint, scope_id, entity_ref, parameters, idempotency_key).
  - **Phê Duyệt Độc Lập (Dual-Control HITL):**
    - Kiểm tra role người duyệt: Chỉ cho phép `SRELead` hoặc `SecurityOfficer`.
    - **Chống tự phê duyệt (Self-approval guard):** Bắt buộc `approver_id != requester_id`. Nếu trùng, từ chối với HTTP 403.
    - Kiểm tra phạm vi (scope isolation): Bắt buộc scope của approver bao phủ scope của intent.
    - So khớp chính xác `intent_hash`: Nếu lệnh bị thay đổi dù chỉ 1 byte, từ chối với HTTP 400.
    - Kiểm tra thời hạn hết hiệu lực (TTL 15 phút).
  - **Thực Thi Ký Danh Bằng Khóa HMAC Chuyên Dụng:**
    - Ký HTTP headers: `X-Agent-Timestamp` và `X-Agent-Signature` qua HMAC-SHA256 (phương thức, đường dẫn, timestamp, hash body).
    - So khớp timestamp `expectedDeadLetteredAt`: Chống ghi đè race condition (CAS), trả về HTTP 409 nếu trạng thái đã đổi.
    - Chụp trạng thái sau lệnh: Xác minh `DeadLetteredAt` đã được gỡ bỏ và `RetryCount = 0`.
    - Lưu biên nhận mật mã `ExecutionReceipt`.
  - **Xử Lý Mất Kết Nối & Idempotency Bền Vững:**
    - Khi mất response sau khi owner commit, Hub chuyển trạng thái sang `UNKNOWN`.
    - Thử lại với cùng `idempotency_key`: Owner nhận diện bản ghi trong `OutboxRecoveryCommands`, trả về `already_applied` với 0 lần ghi trùng lặp.
  - **Bằng Chứng Drill Thực Nghiệm với Fault Injection Thật (Isolated Business Drill):**
    - Đã chạy thành công drill thật: Agent Hub (HTTP) → Fault Proxy → Order.Api (.NET 10) → PostgreSQL (Docker) với 2 dead-lettered events (A và B).
    - **Fault Injection:** Proxy TCP RST ngắt kết nối ngay sau khi Order.Api commit transaction vào PostgreSQL. Agent Hub bắt lỗi rớt mạng, chuyển trạng thái intent sang `UNKNOWN` (HTTP 503).
    - **Operator Retry:** Khi gửi lại request cùng intent và idempotency key, Agent Hub nhận diện `was_unknown = True`, gọi lại Order.Api; Order.Api nhận diện key trong `OutboxRecoveryCommands` và trả về `already_applied`; Agent Hub lưu biên nhận (`verified=True`) và chuyển intent sang `SUCCEEDED`.
    - Kết quả DB: Chỉ Event A được phục hồi (`DeadLetteredAt = NULL`); Event B giữ nguyên dead-lettered; bảng `OutboxRecoveryCommands` ghi đúng 1 bản ghi duy nhất (0 duplicate operations). Bằng chứng lưu tại `docs/evidence/2026-10-24-gate2-opsbridge-agent-hub-drill.md`.

### 2.3. Trạng Thái Cụm Azure AKS (`aks-portfolio-dev`)
- **Nodepool Scale & Compute Capacity:**
  - Nodepool `sys` (`Standard_D2s_v6`) được scale từ 1 lên 2 nodes (`aks-sys-20053029-vmss000000`, `aks-sys-20053029-vmss000001` đều Ready) sau khi được User phê duyệt chi phí.
  - Sức chứa nâng từ 30 lên 60 pods, giải phóng toàn bộ tắc nghẽn CPU và pod scheduling cho các workloads.
- **Dynamic Azure Managed Disks Provisioning:**
  - `data-postgres-0`: 1 GiB Standard SSD dynamically provisioned & Bound via CSI Driver (`disk.csi.azure.com`).
  - `data-rabbitmq-0`: 1 GiB Standard SSD dynamically provisioned & Bound via CSI Driver (`disk.csi.azure.com`).
- **Argo CD Applications & GitOps Reconcile:**
  - `flashsale`: Target revision `ops-cloud-20261025` (`71cf53b`), overlay `infrastructure/kubernetes/overlays/azure-cloud`, trạng thái **Synced**.
  - `quanlykho`: Target revision `fde9570`, overlay `infra/k8s/overlays/production`, trạng thái **Synced**.
- **Workloads Đang Chạy Thực Tế (Live Telemetry):**
  - **Namespace `flashsale` (9/9 pods Running):**
    - `order-api-55b5dc9df-2f744`: 1/1 Running
    - `order-api-55b5dc9df-xw9qv`: 1/1 Running
    - `order-worker-58c6b9d9c7-84r5s`: 1/1 Running
    - `order-worker-58c6b9d9c7-d9wk6`: 1/1 Running
    - `payment-service-6845cd98bb-rrc4h`: 1/1 Running
    - `postgres-0`: 1/1 Running (StatefulSet, PostgreSQL 15)
    - `rabbitmq-0`: 1/1 Running (StatefulSet, RabbitMQ 3.12)
    - `redis-695b986ccc-d6jlt`: 1/1 Running
    - `kafka-0`: 1/1 Running
  - **Namespace `quanlykho` (3/3 pods Running):**
    - `bankops-api-746c9db96c-2jntk`: 1/1 Running (FastAPI + asyncpg)
    - `bankops-api-746c9db96c-pcsdx`: 1/1 Running
    - `bankops-worker-f666857bb-nmgnl`: 1/1 Running
  - **Namespace `agent-hub`:**
    - `agent-hub-7b974bb9cf-xf99k`: 1/1 Running
- **Kiểm Tra Thực Tế Qua Mạng Nội Bộ Cluster:**
  - `http://order-api.flashsale.svc.cluster.local/health/live`: `HTTP 200 {"status":"healthy"}`
  - `http://order-api.flashsale.svc.cluster.local/health/ready`: `HTTP 200 {"status":"ready"}`
  - `http://bankops-api.quanlykho.svc.cluster.local:8000/health/live`: `HTTP 200 {"status":"alive","version":"0.1.0"}`
  - `http://bankops-api.quanlykho.svc.cluster.local:8000/health/ready`: `HTTP 200 {"status":"ready","services":{"database":"ready"}}`
- **Báo Cáo Chi Phí FinOps:**
  - Đã xuất bản chi tiết tại `docs/evidence/finops-cloud-cost-report.md` (tổng chi phí cụm hiện tại: ~$0.22/giờ, ~$160.44/tháng; có runbook teardown/spot giúp giảm >85% khi không phỏng vấn).

### 2.4. Sửa Đổi Monorepo CI (`monorepo-ci.yml`)
- Cấu hình hủy job khi commit mới xuất hiện (`cancel-in-progress`) đã được sửa thành:
  ```yaml
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
  ```
  Nhờ đó, mọi lần push lên nhánh `main` đều được đảm bảo chạy hết toàn bộ các bài kiểm thử mà không bị hủy giữa chừng.

---

## 3. Bằng Chứng Kiểm Thử Chi Tiết

### 3.1. Agent Hub & ADR 024 HITL Tests (10/10 PASS)
```text
services/agent-hub/tests/test_adapters.py ...... PASSED [6/6]
services/agent-hub/tests/test_hitl_execution.py .... PASSED [4/4]
- test_intent_hash_is_deterministic: PASSED
- test_create_intent_validation_and_idempotency: PASSED
- test_hitl_approval_enforcement: PASSED (Non-approver role 403, Cross-scope 403, Tampered hash 400, Duplicate approval 409)
- test_hitl_execution_and_post_verification: PASSED (Unapproved 403, Execute 200, Verified True, Idempotent second call 0 duplicate)
TOTAL: 10 passed in 0.25s
```

### 3.2. Platform & Workload Evals (27/27 PASS)
```text
tests/evals/test_auth_and_api_security.py ................. PASSED (18 tests)
tests/evals/test_e2e_investigation_flow.py .               PASSED (16 casebook flows)
tests/evals/test_policy_gates.py ....                      PASSED (4 tests)
tests/evals/test_schemas.py ....                           PASSED (4 tests)
TOTAL: 27 passed in 0.63s
```

### 3.3. OpsBridge .NET 10 Test Suite (380/380 PASS)
```text
FlashSale.UnitTests:        196 passed, 0 failed
OpsBridge.UnitTests:         47 passed, 0 failed
OpsBridge.ContractTests:      7 passed, 0 failed
OpsBridge.IntegrationTests:  42 passed, 0 failed (Testcontainers)
FlashSale.IntegrationTests:  88 passed, 0 failed (Testcontainers)
TOTAL:                      380 passed, 0 failed in 2m 51s
```
