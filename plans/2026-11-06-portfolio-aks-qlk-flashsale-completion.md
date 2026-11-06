# Kế hoạch hoàn thành portfolio: AKS, QuanLyKho, FlashSale

**Lập ngày:** 2026-11-06. **Phạm vi:** `AKS-SRE-Platform`, `QuanLyKho`, `FlashSale-Backend`. CreditFlow không thuộc phạm vi kế hoạch này. Đây là kế hoạch và định nghĩa nghiệm thu, chưa phải chứng nhận >90% hoặc phê duyệt go-live.

## 0. Khám phá tài liệu và khóa phạm vi

Trước khi sửa hoặc triển khai, người thực hiện đọc `AGENTS.md` của từng repo, kiểm tra branch/HEAD/worktree, CI và môi trường thực. Nếu repo có `.codegraph/`, dùng CodeGraph trước tìm kiếm mã. Ba repo được kiểm tra ngày 2026-11-06 đều không có `.codegraph/`. Mỗi gate phải có source SHA, image digest/revision, môi trường, thời điểm UTC, lệnh/kịch bản, expected/actual, raw log đã che nhạy cảm và rollback target. Bằng chứng SHA cũ là đầu vào điều tra, không tự động là PASS cho release mới.

| Repo | Nguồn hiện hành cần đọc | Mẫu có thể dùng | Giới hạn cần tránh |
| --- | --- | --- | --- |
| AKS | [`docs/evidence/2026-11-06-offline-validation.md`](../docs/evidence/2026-11-06-offline-validation.md), [`docs/evidence/2026-11-04-portfolio-gate-matrix.md`](../docs/evidence/2026-11-04-portfolio-gate-matrix.md), [`docs/evidence/2026-11-05-A13-calico-policy-6470094.md`](../docs/evidence/2026-11-05-A13-calico-policy-6470094.md), `docs/runbooks/azure-teardown-runbook.md` | A13 probe 200 → 000 → 200; bảng evidence theo gate trong matrix | Terraform mock, CI, kind và Pages không chứng minh runtime Azure. AKS đã teardown ngày 05/11; không dựa vào trạng thái cloud cũ. |
| QuanLyKho | `/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md`, `docs/portfolio/journey-evidence.md`, `docs/runbooks/release-authority.md`, `docs/QA_PLAN.md` | `backend/tests/test_portfolio_ai_checker_demo.py` cho receipt → approve → issue → audit → rollback; `Makefile` cho lệnh kiểm chứng | Local fake-data journey và Pages synthetic không đóng 21 cloud/UI/device gate. Migration 034 hiện đã được track; không dùng ghi chú cũ nói nó untracked. |
| FlashSale | `/Users/mainguyenbinhtan/Downloads/FlashSale-Backend/README.md`, `README_DEPLOY.md`, `docs/portfolio/sacombank-jd-evidence.md`, `docs/deployment/production-approval-checklist.md`, `src/payment-service-java/AKS_DEPLOYMENT.md` | `src/payment-service-java/scripts/smoke-local.sh`; `.github/workflows/cloud-deploy.yml` cho preview/production tách biệt | Repo hiện là **Java payment-service mô phỏng**. Các tài liệu cũ về .NET, Order.Api, OpsBridge, zero-oversell và Kafka không mô tả sản phẩm hiện tại. Không gọi mô phỏng là PSP thật hoặc bật demo profile trong production. |

**Lệnh được tài liệu hiện hành cho phép:** AKS: `terraform fmt -check -recursive`, `terraform -chdir=<root> validate/test -no-color`, `python3 -m pytest -q tests`, `python3 tests/test_gates.py`, `kubectl kustomize <root>`, `python3 scripts/policy-gate.py`, `python3 gitops/validate-gitops.py --repo-map gitops/repo-map.ci.yaml`. QuanLyKho: `make test-backend`, các lệnh lint/Flutter/E2E trong `Makefile`, và workflow publish thủ công trong `docs/runbooks/release-authority.md`. FlashSale: `mvn -B clean verify` trong `src/payment-service-java`, Compose + `smoke-local.sh`, `kubectl kustomize k8s` cho manifest hiện hành; deployment theo `README_DEPLOY.md`. Không thay lệnh bằng API/flag suy đoán.

## 1. Điểm xuất phát và cách tính mới

| Repo | Gate | Trạng thái có thể nói hôm nay | Việc còn thiếu |
| --- | --- | --- | --- |
| AKS | A01–A16, 14 gate thực tế trong ma trận | Baseline được ghi nhận là **12/14**; A13 và A16 OPEN. Offline kiểm chứng trên `3fac87e`, trong khi branch hiện tại đã đi tiếp. | A13 cần proof trên final SHA; A16 cần Azure runtime, state/cost, telemetry, restore/rollback. PR #30 SonarCloud từng báo `Not authorized`; kiểm tra lại credential/check hiện tại. |
| QuanLyKho | 21 MVP journey ID trong checkpoint | **0/21** cloud acceptance; local evidence đã tiến bộ, gồm migration 034 và backend fake-data smoke trên SHA cũ. | Cùng release API/UI, cloud DB, hai tài khoản UAT, thiết bị thật, rollback và log theo từng ID. |
| FlashSale | **F01–F10 mới đề xuất dưới đây** | Chưa chấm điểm. Evidence `07b77bd` ghi 76 test và local build/scan/smoke; HEAD đã đổi. Preview/prod cloud chưa được chứng minh; Render prod hook từng 404. | Khóa acceptance F01–F10 với owner trước khi tính baseline; re-run trên final SHA, chứng minh preview, cloud, rollback và production release. |

**Công thức sau khi owner chấp nhận F01–F10:** `score = (AKS_PASS/14 + QLK_PASS/21 + FlashSale_PASS/10) / 3`; yêu cầu `score > 0,90`, không đổi mẫu số giữa chừng và không tính gate thiếu evidence. Chưa công bố điểm mới vì FlashSale chưa có baseline được duyệt. Mục tiêu thực thi là **14/14 + 21/21 + 10/10**. Điểm >90% là thước đo portfolio; quyết định go-live là một cổng độc lập theo từng hệ thống.

### Bộ gate FlashSale đề xuất để owner khóa tại C0

| ID | Acceptance và môi trường bắt buộc |
| --- | --- |
| F01 | `mvn -B clean verify` và Java/Testcontainers tests xanh trên candidate SHA; không skip. LOCAL/CI. |
| F02 | Compose: PostgreSQL, Redis, RabbitMQ, health/readiness, login và smoke payment thành công. LOCAL. |
| F03 | Same-key replay không tạo thêm payment; conflicting replay trả 409; decline/timeout và RabbitMQ event/outbox có negative control. LOCAL + candidate cloud. |
| F04 | Auth/RBAC fail closed, demo profile không chạy ở production; secret, dependency và image HIGH/CRITICAL scans xanh. CI + candidate cloud. |
| F05 | Load test theo ngưỡng được owner chốt; ghi p95, error rate, RPS, double-effect count từ chạy thật. STAGING. Không lấy số mục tiêu trong tài liệu làm số đo. |
| F06 | Image immutable digest, source SHA, SBOM/provenance và manifest/release ref khớp; deployment không dùng `:latest`. CI + STAGING. |
| F07 | Preview Java backend thật, phụ thuộc thật, health và payment E2E trên endpoint công khai/private được phép; demo frontend chỉ là phụ trợ. STAGING. |
| F08 | Log/metric/alert cho lỗi payment, broker, DB và idempotency; fault drill chứng minh tín hiệu đến nơi trực vận hành. STAGING. |
| F09 | Backup/restore DB, rollback image/schema, trước/sau và RTO/RPO đo được; dữ liệu payment không double-effect. STAGING. |
| F10 | Production config/secret separation, identity model, owner review, controlled release và post-deploy smoke trên đúng digest; nếu còn mock login/PSP thì chỉ được phê duyệt **demo production**, không tuyên bố thanh toán thật. PROD. |

## 2. Pha C0 — khóa release và điều kiện bắt đầu

**Thực hiện:** Chọn một release candidate SHA ở mỗi repo; lưu `git status`, CI URL, image digest/revision, sơ đồ dependencies và rollback target. Owner chốt F01–F10, production của FlashSale là **demo payment** hay cần PSP/IdP thật, môi trường Azure/Render được phép, trần chi phí, state owner, tài khoản UAT/thiết bị và người có quyền quyết định go-live. Kiểm tra GitHub Environment reviewer và secrets; không sao chép giá trị secret vào log. Tạo bảng gate mới trong tài liệu evidence, giữ ma trận CreditFlow ngày 05/11 như lịch sử, không sửa ngược số liệu cũ.

**Hoàn tất khi:** Có release manifest ba SHA/digest, owner và tiêu chí PASS cho từng gate, cost cap, môi trường staging/production, rollback target; CI/Sonar thật chạy trên candidate SHA. Nếu thiếu đầu vào, ghi `BLOCKED` theo ID và tiếp tục phần offline độc lập.

**Guard:** Không dùng `main` trôi, `:latest`, scanner skip, chữ ký placeholder hoặc một health 200 làm bằng chứng release.

## 3. Pha C1 — đóng kỹ thuật offline và tạo candidate bất biến

1. **AKS:** Re-run fmt/validate/test cả năm Terraform roots, Python/G1–G16, 10 Kustomize roots, policy/GitOps external checkout và CI trên final SHA. Dùng A13 Calico probe trong tài liệu làm mẫu; chạy lại 200 → deny/000 → allow/200 trên final SHA, lưu raw log và teardown. Không suy ra Azure NetworkPolicy từ kind.
2. **QuanLyKho:** Chạy `make test-backend`, lint, Flutter/build/E2E theo `Makefile`; chứng minh migration 001→034 trên DB trống và upgrade từ snapshot trước 034, backup/restore và rollback. Dùng test journey backend hiện có làm mẫu rồi thêm negative cases theo `docs/QA_PLAN.md`. Đóng lỗi Redis test chỉ khi tái hiện và xác định nguyên nhân; không che flaky run.
3. **FlashSale:** Re-run Java `mvn -B clean verify`, Compose smoke, Docker build/Trivy, auth/idempotency/event negative tests và load rehearsal trên candidate SHA. Xác minh `render.yaml`/workflow và các endpoint theo README hiện hành. Sửa mã hoặc test khi có lỗi thực; không kéo các gate .NET/OpsBridge cũ vào release Java.

**Hoàn tất khi:** F01–F04 có evidence mới; AKS A13 được quyết định trên final SHA; QLK migration/rollback lab có log; mọi repo có candidate digest, CI green và danh sách open gate chính xác. Không tự chấm QLK cloud gate từ kết quả local.

## 4. Pha C2 — staging có thể khôi phục, theo thứ tự phụ thuộc

1. **Nền cloud AKS (A16):** đối chiếu Terraform backend/state và resource inventory, quota, chi phí dự kiến, budget/cost cap. Sau khi plan được lưu và review, dựng hoặc chọn staging có đường truy cập private được duyệt, user node pool đủ scheduling; triển khai Argo CD/GitOps, gateway, workload, observability. Kiểm tra trên Azure thật: node/pod, sync, policy deny/allow, telemetry/alert, backup/restore và rollback. Thu dọn hoặc giữ môi trường theo quyết định chi phí, ghi inventory cuối.
2. **QuanLyKho release:** tạo DB/API/frontend staging cô lập; snapshot trước migration; publish image bằng workflow thủ công theo `docs/runbooks/release-authority.md`, PR release-ref riêng ở AKS, pin digest. Kiểm tra API/UI cùng SHA và schema version, rollback trước khi chạy UAT. Chạy 21 journey theo từng ID trong checkpoint: catalog/receipt/approval/FEFO/damage/adjust; shift/alert; report/RBAC/audit; offline native và platforms trên thiết bị thật. Mỗi ID có actor, request/response đã che nhạy cảm, DB before/after, UI/device proof và negative case.
3. **FlashSale staging:** publish immutable Java image và triển khai preview theo `README_DEPLOY.md` hoặc AKS validation path đã được chọn tại C0. Sửa Render hook 404 bằng cách xác minh hook/secret với owner, rồi chạy E2E login/payment/idempotency/broker, load test, monitoring, fault/restore/rollback trên đúng revision. Không bật demo profile trên production; nếu thiếu PSP/IdP thật, giới hạn sản phẩm ở demo payment.

**Hoàn tất khi:** A16, 21 QLK ID và F05–F09 có raw evidence đúng môi trường/SHA, hoặc còn OPEN/BLOCKED rõ lý do. CI và deployment phải trỏ về cùng release manifest. Không triển khai QLK/FlashSale vào AKS chỉ để nâng điểm nếu C0 đã chọn môi trường staging khác phù hợp acceptance.

## 5. Pha C3 — chốt điểm và go-live

Release owner khóa ba SHA/digest/revision; rerun mọi gate bị ảnh hưởng bởi commit cuối; kiểm tra CI/Sonar/security không skip. Tính lại score theo công thức đã chốt; xuất bảng PASS/FAIL/OPEN từng ID kèm URL/log, chi phí thực tế hoặc ước tính được kiểm chứng, rollback target và hạn mức. Thử rollback production candidate trong staging và post-deploy smoke theo runbook. Người có thẩm quyền ghi quyết định riêng: `AKS`, `QuanLyKho`, `FlashSale` = `APPROVED`/`WAITING`/`REJECTED`, tên, ngày, phạm vi và điều kiện. Chỉ quảng bá go-live cho các hệ thống được duyệt và có toàn bộ gate P0 bắt buộc PASS; portfolio >90% tự nó không thay thế phê duyệt.

**Điều kiện dừng:** Sai SHA/digest; không có restore đã thử; cloud bill/quota không có owner; scanner đỏ hoặc skip; QLK thiếu journey UAT bắt buộc; FlashSale còn demo auth/PSP nhưng được mô tả như thanh toán thật; telemetry/rollback không đo được. Khi dừng, ghi blocker và giữ release cũ.

## Giao việc theo vùng sở hữu

| Owner | File/trách nhiệm | Bàn giao |
| --- | --- | --- |
| Platform | AKS `terraform/`, `deploy/`, `gitops/`, `scripts/`; A13/A16 | Saved plan, Azure inventory, raw policy/runtime/restore/cost evidence |
| QLK backend | QLK `backend/`, migration, API release | Migration/backup/rollback và API SHA/digest |
| QLK QA | QLK `frontend/`, `backend/tests/`, `docs/qa/evidence/` | 21 ID cloud/UI/device logs |
| FlashSale Java | `src/payment-service-java/`, Java tests, Docker | F01–F05, F07–F09 logs trên đúng Java revision |
| FlashSale release | `.github/workflows/`, `render.yaml`, `README_DEPLOY.md` | F06/F10 image/deploy/approval evidence |
| Release coordinator | Ma trận mới, release manifest, status, CI links | Score chính xác và quyết định go-live riêng |

Mỗi nhóm dùng branch/worktree riêng, không ghi đè thay đổi của nhóm khác. Mỗi đợt bàn giao có commit/PR/CI URL, lệnh verify, raw evidence và trạng thái `DONE/PARTIAL/BLOCKED`. Việc cloud mutate cần saved plan được review, cost cap và quyền từ owner theo C0.
