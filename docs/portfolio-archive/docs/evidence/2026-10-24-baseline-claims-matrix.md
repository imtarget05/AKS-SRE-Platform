# Bảng Đối Chiếu Hiện Trạng Bằng Chứng và Các Tuyên Bố Kỹ Thuật (Phase 1 Update)

**Thời điểm kiểm tra live:** 2026-10-24 22:54 UTC+7
**Tiêu chuẩn đối chiếu:** [PHASES.md](../../PHASES.md), [STATUS.md](../../STATUS.md), [ADR 025](../adr/025-canonical-repositories-source-of-truth.md), và [2026-10-24-canonical-reconciliation-handoff.md](../plans/2026-10-24-canonical-reconciliation-handoff.md).

Mọi tuyên bố kỹ thuật (claims) bắt buộc phải đối chiếu với Git commit thật, GitHub Actions run thật (không skipped), dữ liệu thật và tài nguyên cluster thật. Các trạng thái được chuẩn hóa gồm:
- **`VERIFIED`**: Có bằng chứng máy kiểm tra thực tế (exact SHA, CI xanh đầy đủ các job test, dữ liệu hoặc cluster state khớp).
- **`FAILED`**: Đã chạy nhưng kiểm tra thất bại, hoặc tuyên bố sai lệch so với trạng thái hệ thống thực tế.
- **`NOT_VERIFIED`**: Chưa được kiểm chứng trên môi trường chỉ định hoặc commit chưa vào remote canonical main.

---

## 1. Bảng Ma Trận Tuyên Bố Kỹ Thuật (Claims Matrix)

| STT | Thành phần | Tuyên bố kỹ thuật (Claim) | Nguồn bằng chứng & Điểm kiểm tra | Trạng thái Live | Bằng chứng thực tế / Phân tích chi tiết |
|:---:|:---|:---|:---|:---:|:---|
| 1 | **Retail Finance** | Outlet-scoped settled transactions feed (`GET /api/settlement/outlet-feed`) bảo đảm cô lập chi nhánh và phân quyền (Admin vs Auditor), chạy trọn vẹn 33 MySQL Testcontainers IT. | `retail-finance-core-platform` commit `11620ed67c5c6e208a3af1bd72e7cf0a96b67271` trên `origin/main`. | **`VERIFIED`** | `backend-ci` run [40107593770](https://github.com/imtarget05/retail-finance-core-platform/actions/runs/40107593770): **3/3 jobs passed 100%**: Unit tests (45s), Reconciliation tests (10s), Integration tests với real MySQL 8 (1m27s). Đã khắc phục lỗi Docker API 1.32 bằng Testcontainers 1.20.4 + Docker API 1.44 configuration. |
| 2 | **Retail Finance** | Migration V2 (thêm outlet_id, index, foreign key) là "zero downtime / không khóa bảng" trên production. | Hồ sơ CV Draft & Architecture notes. | **`NOT_VERIFIED`** | Chưa từng đo tải hoặc chạy migration công cụ online schema change (pt-online-schema-change / gh-ost) trên MySQL production. Claim này bị cấm sử dụng cho đến khi có benchmark thật. |
| 3 | **OpsBridge** | 50 contenders tranh chấp 10 units flash sale: 10 accepted, 40 rejected (409), 0 overselling, tính nhất quán Redis và PostgreSQL được bảo toàn. | `FlashSale-Backend` commit `b507464`, CI run [40096911868](https://github.com/imtarget05/FlashSale-Backend/actions/runs/40096911868), k6 load test logs. | **`VERIFIED`** | Bằng chứng k6 và Testcontainers PostgreSQL/Redis chứng minh không có oversell; status 409 trả về đúng cho 40 lượt dư. |
| 4 | **OpsBridge** | API phục hồi outbox đơn lẻ có chữ ký HMAC (`/internal/agent/outbox/{id}/requeue`), kiểm tra `MessageId` + `DeadLetteredAt`, idempotency, concurrency không double effect và ghi audit `OutboxRecoveryCommands`. | `FlashSale-Backend` PR #8 merged vào `origin/main` tại commit `64cd39ba6550fe4414e14dfe70d4a73bb222684d`. | **`VERIFIED`** | CI run [40108742539](https://github.com/imtarget05/FlashSale-Backend/actions/runs/40108742539) (**12 passed, 3 skipped: sonarqube, release-push, gitops-update**) và run [40108742560](https://github.com/imtarget05/FlashSale-Backend/actions/runs/40108742560) (k6 passed). Đã bổ sung test concurrency 2 request đồng thời cùng key, xác nhận chỉ 1 audit được ghi và trạng thái `already_applied`. |
| 5 | **QuanLyKho** | Bộ test 714 tests pass, keyset pagination cursor hoạt động chuẩn xác, hành trình maker-checker được xác minh trên PostgreSQL 16. | `QuanLyKho` commit `c38d724d6650fb8851ab1d9d93af0b5df50bd3f5`, CI run [40109783561](https://github.com/imtarget05/QuanLyKho/actions/runs/40109783561). | **`VERIFIED`** | Toàn bộ 714 test (đơn vị & tích hợp) pass trên CI canonical và monorepo. Keyset pagination giải quyết triệt để lỗi test trên DB tích tụ dữ liệu. |
| 6 | **QuanLyKho** | Triển khai tự động QuanLyKho lên production cloud (Azure Container Apps). | `QuanLyKho` `.github/workflows/deploy.yml`, run [40155519980](https://github.com/imtarget05/QuanLyKho/actions/runs/40155519980) trên commit `fde9570a390babbffd9149f5e408771cb9300bb0`. | **`VERIFIED`** (Workflow Guard) / **`NOT_VERIFIED`** (Cloud runtime) | Workflow deploy đã được cấu hình job-level credential guard: khi repository secrets thiếu `AZURE_CLIENT_ID`, bước deploy được skip sạch sẽ (`0s`), không làm đỏ CI trên main. Triển khai cloud thật chưa kích hoạt vì yêu cầu human review và OIDC secret. |
| 7 | **QuanLyKho** | K8s Production Overlay sẵn sàng đồng bộ GitOps qua Envoy Gateway với 0 Secret và 0 CHANGE_ME trong Git. | `QuanLyKho` `infra/k8s/overlays/production/` commit `fde9570a390babbffd9149f5e408771cb9300bb0`. | **`VERIFIED`** | Kustomize render hoàn toàn sạch (0 Secret, 0 CHANGE_ME, Envoy Gateway HTTPRoute `quanlykho.internal` trỏ tới `bankops-api:8000`). Bộ test backend pass 714/714 trên Postgres cô lập (`make test-backend`). |
| 8 | **AKS Platform** | Cụm AKS `aks-portfolio-dev` đã cài đặt Gateway API CRD v1.1.0 và KEDA v2.16. | `kubectl --context aks-portfolio-dev get crd`, namespaces `keda`, `agent-hub`. | **`VERIFIED`** | Pods `keda-operator` (1/1 Running), `keda-admission-webhooks` (1/1 Running). Gateway API CRDs đã đăng ký trên cluster. |
| 9 | **AKS Platform** | Golden path GitOps: Argo Applications `flashsale` và `quanlykho` cấu hình overlay cloud với targetRevision bất biến, sync policy manual first cutover, validate 29/29 objects render và khớp commit checkout. | `AKS-SRE-Platform` commit `1ebbb6ff3f50f4066d8e42e206f623e1a45150a9`. | **`VERIFIED`** (Cấu hình & Render) / **`PENDING_APPROVAL`** (Cloud sync) | Manifests trỏ tới SHA bất biến (`eae0ebf` cho FlashSale, `fde9570` cho QuanLyKho). Đã chạy `validate-gitops.py --repo-map gitops/repo-map.yaml --require-external` kiểm tra toàn diện 3 source ngoài đạt 29/29 passed, 0 failed, 0 not-present (xác nhận cả 3 application đều khớp commit checkout). `check-cloud-cutover.py` exit 0 (CI run [40157466065](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/40157466065)). OIDC federated login (positive control) và negative control (rejection AADSTS700213 trên unbound subject, masked token) đều đạt 100% trong CI run [40157466054](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/40157466054). Trên cụm AKS thật (`aks-portfolio-dev`), Argo Application hiện trỏ `main` và overlay `local` ở trạng thái `OutOfSync/Missing` (chưa deploy pod lên cloud) chờ human approval gate. |
| 10 | **Agent Hub** | Agent Hub hoạt động trên cụm AKS `aks-portfolio-dev`. | `kubectl --context aks-portfolio-dev get pods -n agent-hub`. | **`VERIFIED`** (Pilot pod) / **`NOT_VERIFIED`** (Bản HITL mới trên AKS) | Pod `agent-hub-7b974bb9cf-xf99k` đạt trạng thái `1/1 Running` trên AKS `aks-portfolio-dev` với image pilot `acrflashsalep6.azurecr.io/agent-hub:sha-4457b78`. Bản code HITL recovery mới chưa được deploy lên AKS mà được kiểm chứng đầy đủ trong isolated drill. |
| 11 | **Agent Hub** | Cơ chế thực thi HITL bảo đảm ràng buộc intent đơn lẻ, HMAC signing, fault injection rớt mạng sau commit chuyển intent sang `UNKNOWN`, và operator retry nhận `already_applied` với 0 duplicate DB mutations. | `Senior-Engineering-Portfolio` drill artifact `docs/evidence/2026-10-24-gate2-opsbridge-agent-hub-drill.md`. | **`VERIFIED`** (Môi trường cô lập) | Drill độc lập Agent Hub $\rightarrow$ Proxy $\rightarrow$ Order.Api $\rightarrow$ PostgreSQL: Injected TCP RST proxy làm rơi response sau commit của Order.Api; Agent Hub nhận biết lỗi rớt mạng, chuyển intent sang `UNKNOWN` (HTTP 503); operator retry cùng key nhận `already_applied` receipt (`verified=True`), intent chuyển `SUCCEEDED`; DB ghi đúng 1 row duy nhất trong `OutboxRecoveryCommands`, Event B giữ nguyên dead-lettered. |

| 12 | **Monorepo CI** | Commit `a7229d5` chứng minh toàn bộ 4 hệ thống và Agent Hub đều pass CI trên GitHub Actions. | `Senior-Engineering-Portfolio` run [40104985515](https://github.com/imtarget05/Senior-Engineering-Portfolio/actions/runs/40104985515). | **`FAILED`** (Tuyên bố ngộ nhận) | Run `40104985515` chỉ chạy job path filter trong 12 giây; cả 5 job test đều bị `skipped` do commit chỉ sửa docs. Run chứng minh 6/6 jobs test xanh thực tế là [40104051421](https://github.com/imtarget05/Senior-Engineering-Portfolio/actions/runs/40104051421) trên SHA `074a494b25c22c477ea34ce6fc367cff3a23c02c`. |

---

## 2. Kết Luận Phase 0 & Phase 1 (Retail Ledger + Ops Flash Sale Baseline)

- **Phase 0 (Baseline & Hợp đồng AI coding):** **`VERIFIED`**. Hợp đồng exact SHA, source of truth từ remote git, ranh giới 2 component active được duy trì nghiêm ngặt.
- **Phase 1A (Retail Finance):** **`VERIFIED`**. CI run [40107593770](https://github.com/imtarget05/retail-finance-core-platform/actions/runs/40107593770) **100% GREEN** trên commit `11620ed67c5c6e208a3af1bd72e7cf0a96b67271` (`main`), chứng minh account opening atomic và replay không double-post trên 33 MySQL Testcontainers IT.
- **Phase 1B (OpsBridge/FlashSale):** **`VERIFIED`**. PR #8 đã squashed and merged vào `main` tại commit `64cd39ba6550fe4414e14dfe70d4a73bb222684d`; CI run [40108742539](https://github.com/imtarget05/FlashSale-Backend/actions/runs/40108742539) (12 passed, 3 skipped: sonarqube, release-push, gitops-update) và k6 run [40108742560](https://github.com/imtarget05/FlashSale-Backend/actions/runs/40108742560) **100% GREEN** trên exact merge SHA, chứng minh 50 contenders tranh chấp 10 units: 10 accepted, 40 rejected (409), 0 overselling.
- **Trạng thái:** **`PHASE 1 CLOSED (PASSED)`**.

---

## 3. Kết Luận Phase 2 (Quyền Dữ Liệu và Hành Trình Kho)

- **Phase 2A (Retail Outlet Scope):** **`VERIFIED`**. Phân quyền object-level theo outlet, negative permission matrix và migration V2 chạy qua MySQL integration test.
- **Phase 2B (QuanLyKho Canonical Journey):** **`VERIFIED`**. Bộ test 714 tests pass trên CI run [40109783561](https://github.com/imtarget05/QuanLyKho/actions/runs/40109783561) và Postgres 16 cô lập (`make test-backend`). Keyset pagination cursor giải quyết triệt để lỗi test trên DB tích tụ dữ liệu.
- **Trạng thái:** **`PHASE 2 CLOSED (PASSED)`**.

---

## 4. Kết Luận Phase 3 (Fault Recovery và Platform Workload Thứ Nhất)

- **Phase 3A (OpsBridge Fault Matrix):** **`VERIFIED`**. API phục hồi outbox đơn lẻ HMAC (`/internal/agent/outbox/{id}/requeue`), idempotency key và audit log `OutboxRecoveryCommands` merged tại `64cd39b`.
- **Phase 3B (AKS Platform Golden Path Đầu Tiên Trên Kind):** **`VERIFIED TRÊN KIND` / `NOT_VERIFIED TRÊN CLOUD`**.
  - Đã chứng minh golden path triển khai và rollback OpsBridge bằng image digest trên cụm Kind local (`docs/evidence/azure-aks-cloud-deployment-PASS.md` / `scripts/test_zero_downtime_rollback_drill.sh`).
  - Triển khai lên cloud AKS: **`PENDING_APPROVAL`**. Cụm `aks-portfolio-dev` có Gateway API CRDs v1.1.0 và KEDA v2.16 đang hoạt động. Manifests Argo Application trên AKS hiện trỏ nhánh `main` và overlay `local` (`OutOfSync/Missing`). Việc sync lên cloud tuân thủ AGENTS.md Rule 7, chờ human approval gate.
- **Trạng thái:** **`PHASE 3 CLOSED TRÊN KIND (PASSED); CLOUD PROMOTION PENDING_APPROVAL`**.

---

## 5. Kết Luận Phase 4 (Workload Thứ Hai, SRE và FinOps)

- **SRE Alert Lifecycle:** **`VERIFIED TRÊN KIND`**. Đã chạy drill đo đạc vòng đời cảnh báo: metric source down $\rightarrow$ alert `LocalPlatformMetricSourceDown` kích hoạt $\rightarrow$ source phục hồi $\rightarrow$ alert tự động resolve (`docs/evidence/phase7b/platform-alert-drill-PASS.md`).
- **Disaster Recovery Restore Drill:** **`VERIFIED TRÊN KIND`**. Đã thực thi drill drop database thật (`DROP DATABASE "FlashSaleDb" WITH (FORCE)`) và cold restore ra DB cô lập với RTO đo được là **0.570 giây** (`docs/evidence/real-workload-dr-drill-PASS.md`). Phân tích rõ: cold snapshot không có WAL streaming sẽ mất delta transactions giữa thời điểm snapshot và sự cố.
- **Golden Path Hai Workload Trên AKS Cloud:** **`NOT_VERIFIED / PENDING_APPROVAL`**.
  - Mã nguồn GitOps và Kustomize overlays đã sẵn sàng: `validate-gitops.py` đạt **29/29 checks PASS**, xác nhận cả 3 source ngoài (`FlashSale-Backend`, `QuanLyKho`, `AKS-SRE-Platform`) render sạch và khớp chính xác `targetRevision` commit.
  - OIDC Live Gate: [Run 40157466054](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/40157466054) PASS cả positive login và negative rejection trên `AADSTS700213` với token được mask dạng `***`.
  - Trên AKS, Argo Applications `flashsale` và `quanlykho` vẫn ở trạng thái `OutOfSync/Missing` (chưa deploy pod lên cloud) tuân thủ ranh giới an toàn.
- **FinOps & Cloud Cost Report:** **`NOT_VERIFIED`**. Chưa có telemetry chi phí thực tế trên cụm AKS đang chạy.
- **Trạng thái:** **`PHASE 4 PARTIAL (KIND SRE/DR VERIFIED; CLOUD WORKLOAD & COST NOT_VERIFIED / PENDING_APPROVAL)`**.

---

## 6. Kết Luận Phase 5 (Multi-Agent Automation và Hồ Sơ Tuyển Dụng)

- **Agent Hub Dual-Control HITL (ADR 024):** **`VERIFIED TRÊN MÔI TRƯỜNG CÔ LẬP`**.
  - Kiểm chứng trong isolated drill: socket-level TCP RST proxy làm ngắt kết nối sau khi Order.Api commit vào PostgreSQL; Agent Hub nhận biết lỗi rớt mạng, chuyển trạng thái intent sang `UNKNOWN` (HTTP 503); operator retry cùng key nhận `already_applied` receipt (`verified=True`), intent chuyển `SUCCEEDED`; DB ghi đúng 1 row duy nhất trong `OutboxRecoveryCommands`, Event B giữ nguyên dead-lettered.
  - Pod Agent Hub trên AKS là pilot image `acrflashsalep6.azurecr.io/agent-hub:sha-4457b78` (1/1 Running). Bản code HITL recovery mới chưa deploy lên AKS.
- **Hồ Sơ Tuyển Dụng (CVs):** **`VERIFIED`**. Cả 3 file CV ([software-architect.md](../cv/software-architect.md), [senior-platform-engineer.md](../cv/senior-platform-engineer.md), [senior-swe.md](../cv/senior-swe.md)) đã được rà soát và ghi chú phạm vi đo lường trực tiếp tại từng số liệu (gắn chặt với Kind local test harness).
- **Trạng thái:** **`PHASE 5 READY FOR INTERVIEWS (DRILL VERIFIED IN ISOLATED ENVIRONMENT; CVS SCOPED TO KIND)`**.
  - Các phần việc phụ thuộc vào hạ tầng cloud chưa kích hoạt đều được gắn nhãn `NOT_VERIFIED` / `PENDING_APPROVAL` theo đúng chuẩn mực Senior Engineering.
