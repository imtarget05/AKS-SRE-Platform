# Bàn giao AI: hoàn thành ba repo với portfolio >90%

**Chốt trạng thái:** 2026-11-05 05:17 UTC. Đây là kế hoạch thực thi, không phải chứng nhận hoàn thành. Ma trận nguồn là [`docs/evidence/2026-11-04-portfolio-gate-matrix.md`](../docs/evidence/2026-11-04-portfolio-gate-matrix.md); mẫu số cố định: AKS 14, QuanLyKho 21, CreditFlow 22. Baseline được chấp nhận ở checkpoint là 12/14, 0/21, 0/22 = **28,57%**. Mọi PASS phải được kiểm tra lại trên release SHA cuối cùng. Điểm và quyết định go-live phải tách riêng.

## Quy tắc cho mọi AI nhận việc

1. Đọc `AGENTS.md` của repo mình, ma trận gate và checkpoint nguồn. Kiểm tra `git status`, HEAD, PR và CI lúc bắt đầu; trạng thái dưới đây là ảnh chụp, không phải chân lý vĩnh viễn. Nếu có `.codegraph/`, dùng CodeGraph trước khi tìm code. Không sửa hoặc revert công việc của AI khác.
2. Mỗi AI dùng branch/worktree riêng từ nhánh `codex/portfolio-cloud-evidence-20261104`; không cùng sửa một checkout. Chỉ người điều phối hợp nhất từng PR sau review và CI. Ghi rõ owner của file; khi cần sửa file ngoài vùng sở hữu, gửi thay đổi đề xuất cho owner đó.
3. Một gate chỉ PASS khi có raw log đã che nhạy cảm, thời gian UTC, môi trường bắt buộc, source SHA, digest/revision khi triển khai, lệnh/kịch bản, expected/actual và đường rollback. `skip`, HTTP health đơn lẻ, demo synthetic, bằng chứng ở SHA cũ và job scanner không chạy đều không đạt.
4. Không dùng lại token Render, Sonar hoặc Cloudflare đã lộ trong chat. Không đặt secret trong repo, shell history, log hay tài liệu. Không thay dữ liệu thật, IdP ngân hàng, chữ ký Risk/InfoSec/IAM hoặc UAT bằng fixture giả. Giữ production fail-closed.
5. Mỗi task kết thúc bằng commit nhỏ, PR/CI URL, log test và cập nhật evidence theo ID. Báo cáo `DONE/PARTIAL/BLOCKED` kèm bằng chứng; không ghi “production ready” khi gate còn OPEN.

## Trạng thái đầu vào và ngưỡng điểm

| Repo | HEAD khi lập plan | Bằng chứng đã chấp nhận | Vướng mắc chính |
| --- | --- | --- | --- |
| AKS-SRE-Platform | `639098f` | 12/14 ở checkpoint; A13 local Calico proof trên `6470094`; Pages Preview từ `4cd930a` | A13 cần recheck trên final release SHA; A16 Azure private runtime, state và cost chưa xác nhận |
| QuanLyKho | `4f1f03d` | 0/21; CI và external Sonar xanh trên `21366a1`; Pages Preview synthetic cùng SHA | Backend/cloud UI chưa cùng release, migration 034 chưa chứng minh trên cloud, 21 hành trình chưa UAT |
| CreditFlow | `98b8ab7` | 0/22; CI nội bộ xanh trên `98b8ab7`, 14 control có hỗ trợ local | ACA chạy image `:latest` cũ; thiếu IdP, dữ liệu/mô hình, tích hợp và phê duyệt ngân hàng |

Ba PR là AKS #18, QuanLyKho #11, CreditFlow #2. Coverage XML đã được import vào cả ba Sonar scanner. **QuanLyKho external quality gate PASS** trên `21366a1`: new-code coverage 81,8% và security rating 1. **AKS và CreditFlow còn FAIL**: new-code coverage lần lượt 5,5% và 59,3%, ngưỡng 80%. CI trên các commit tài liệu mới phải chạy lại trước khi chốt release. Không tắt hoặc nới gate.

**Cloud checkpoint:** AKS Pages Preview `e7728690.aks-sre-platform.pages.dev` nhúng SHA `4cd930a`; QuanLyKho Pages Preview `cdf21402.quan-ly-kho-tra-sua.pages.dev` có manifest SHA `21366a1`, mode synthetic và `api_release=null`. Production Pages của cả hai project không đổi. [Render Free mirror](../docs/evidence/2026-11-05-render-free-mirror-1c4f9ec.md) `sre-demo-api.onrender.com` đã Live trên commit `1c4f9ec`, chỉ chứng minh demo API. Azure A16 có [infra issue #19](https://github.com/imtarget05/AKS-SRE-Platform/issues/19), chưa có đường truy cập private được duyệt. QuanLyKho `docs/LOCAL_PROJECT_STATUS.md` vẫn là file untracked ngoài phạm vi này, không tự xóa hoặc stage.

Điểm >90 có thể kiểm lại: nếu AKS 14/14 và QuanLyKho 21/21, CreditFlow cần tối thiểu 16/22 (90,91% tổng); nếu AKS 13/14 thì CreditFlow cần 18/22; nếu AKS giữ 12/14 thì cần 19/22. Đây là ngưỡng số học, **không** cho phép bỏ các gate còn lại hoặc phát hành khi P0 production còn mở. Mục tiêu thực thi là đóng đầy đủ mọi gate có thể, không tối ưu điểm bằng cách sửa mẫu số.

## Phân công, quyền sở hữu và thứ tự

| ID / người nhận | Sở hữu file và trách nhiệm | Phụ thuộc | Đầu ra bắt buộc |
| --- | --- | --- | --- |
| H0 — Chủ tài khoản | SonarCloud/GitHub Secrets; rotate các token đã lộ, xác nhận Azure Terraform state, quota và trần chi phí; cấp UAT account/device; chỉ định chủ ngân hàng | Không | Tên secret đã cập nhật, phê duyệt bằng văn bản và giới hạn cloud; không gửi giá trị secret vào chat |
| CI — AI tích hợp CI | Chỉ `.github/workflows/` và script gate liên quan trong ba repo; không sửa business code | H0 cho scanner có credential | CI xanh trên SHA ứng viên, external Sonar xanh, SBOM/secret/dependency scan không skip |
| AKS — AI platform | `local/kind/`, `deploy/`, `gitops/`, `terraform/`, `scripts/` của AKS; không sửa workflows hoặc ma trận trung tâm | H0 cho Azure mutate, CI cho release | A13 và A16 có raw evidence; Terraform/GitOps/render vẫn xanh |
| QLK-API — AI backend | `backend/app/`, `backend/alembic/`, `backend/scripts/`, `infra/modal/` của QuanLyKho; không sửa `backend/tests/`, `frontend/` hoặc workflows | H0 cho cloud DB và UAT | Migration 034 trên target cô lập, API revision/digest, backup và rollback chứng minh được |
| QLK-UI-QA — AI hành trình | `frontend/`, `backend/tests/` cho E2E, `docs/qa/evidence/` của QuanLyKho; không sửa backend implementation | QLK-API contract/release | 21 ID chia nhóm, API/UI và quyền cùng SHA, thiết bị/offline có log |
| CF — AI CreditFlow | `backend/`, `pipeline/`, `frontend/`, `scripts/` của CreditFlow; không sửa workflows hoặc tuyên bố phê duyệt | H0 cho IdP/data/contracts, CI cho release | Production-safe adapters, synthetic staging, 14 control cloud proof; 8 bank gates được giữ OPEN tới khi chủ ký |
| REL — AI điều phối release/evidence | `tasks/plan.md`, `tasks/todo.md`, ma trận AKS và status docs; hợp nhất PR, chốt SHA/digest/revision, tính điểm | Tất cả đầu ra | Bảng PASS/OPEN/FAIL theo ID, CI/evidence link, quyết định go-live riêng và rollback target |

`CI`, `AKS`, `QLK-API`, `CF` có thể bắt đầu song song sau khi tách worktree. `QLK-UI-QA` chuẩn bị test fixtures song song nhưng chỉ chạy cloud acceptance sau release của `QLK-API`. `REL` tổng hợp sau mỗi checkpoint; không tự đánh PASS thay owner kiểm thử.

## Gói việc nhỏ để giao cho AI

### CI-1 — Sonar và release guard (CI; M)

QuanLyKho đã xanh internal/external trên `21366a1`; recheck sau commit tài liệu. AKS Sonar đã import Python coverage nhưng còn 410/434 dòng mới chưa cover, tập trung ở `apps/sre-console/datafeed.js`, `app.js`, `simulation.js` và Node workload. CreditFlow còn 1.358/3.338 dòng mới chưa cover, nhiều nhất ở `backend/app.py`, notification/reconciliation adapters và scripts. Giao AI test riêng từng repo để bổ sung kiểm thử thực và LCOV cho JavaScript; không loại trừ mã sản phẩm khỏi `sonar.sources` để lấy điểm. Kiểm chứng: `gh pr checks` xanh **cả internal lẫn external** trên từng SHA, scan không `skip`, quality gate không bị nới.

### AKS-1 — A13 policy toggle (AKS; M)

Đã chạy kind cô lập với Calico v3.33.0 trên `6470094`: cùng probe cho HTTP 200 → timeout/000 → HTTP 200, có [raw log và policy](../docs/evidence/2026-11-05-A13-calico-policy-6470094.md), cluster tạm đã xóa. Trên final release SHA, re-run và gắn log với SHA đó rồi mới chấm PASS. Gate A13 chỉ đóng cho LOCAL, không suy ra Azure.

### AKS-2a/2b/2c — A16 state/cost/runtime (AKS + H0; ba task M nối tiếp)

**2a — state/cost:** trước mọi mutate, đối chiếu Terraform backend blob/state owner, `az aks nodepool list`, quota/chi phí ước tính và trần chi phí được chủ duyệt. **2b — runtime:** cluster private có hai node System taint `CriticalAddonsOnly`; Azure Run Command hiện không lên pod. Chọn đường truy cập private được duyệt hoặc cấu hình user pool sau phê duyệt chi phí; kiểm tra Argo CD sync, workload, policy và metrics trên **Azure thực**. **2c — recovery:** thực hiện restore và rollback với before/after và image digest/revision. Kiểm chứng: `terraform validate/test/plan`, diff plan được review, inventory trước/sau, drill và hóa đơn/ước tính; không áp dụng Terraform chỉ để lấy điểm.

### QLK-1a/1b/1c — Release backend có thể khôi phục (QLK-API; ba task M nối tiếp)

**1a — nền DB:** đóng nguyên nhân test Redis lần đầu nếu còn tái hiện; chứng minh migration `034_general_ledger_coa` từ DB trống và từ snapshot phiên bản trước. **1b — phát hành cô lập:** tạo target PostgreSQL/FastAPI riêng, backup trước deploy, gắn source SHA và image digest/Modal revision. **1c — recovery:** kiểm tra rollback schema và app từ snapshot. Kiểm chứng: `make test-backend`, Ruff, migration log, DB schema version trước/sau, restore/rollback log. Không sửa production Modal đang chạy từ SHA cũ cho tới khi có điểm khôi phục.

### QLK-2 — Sáu journey kho lõi (QLK-UI-QA; M mỗi 1–2 ID)

`QLK-CATALOG`, `RECEIPT`, `APPROVAL`, `FEFO`, `DAMAGE`, `ADJUST`: dùng dữ liệu UAT riêng, maker/checker khác nhau, đo DB movement và UI sau mỗi hành động; kiểm thử retry/idempotency và expired lot. Mỗi ID là một script/log riêng, không gộp kết quả health. Chạy trên API/frontend cùng release từ QLK-1.

### QLK-3 — Ca và cảnh báo (QLK-UI-QA; M mỗi 1–2 ID)

`SHIFT-OPEN`, `SHIFT-COUNT`, `SHIFT-HANDOFF`, `SHIFT-LOCK`, `ALERT-LOW`, `ALERT-EXPIRY`, `ALERT-VARIANCE`, `ALERT-STREAM`: kiểm tra ba ca, hai người bàn giao, lock/adjust, ngưỡng và SSE reconnect đúng role. Ca thật/ngày vận hành cần UAT owner; test clock mô phỏng chỉ hỗ trợ kỹ thuật.

### QLK-4 — Báo cáo và quyền (QLK-UI-QA; M mỗi 1–2 ID)

`REPORT-XNT`, `REPORT-TOP`, `REPORT-HISTORY`, `RBAC`, `AUDIT`: so số liệu với ledger trong DB, ma trận role/branch bằng tài khoản UAT khác nhau và fault-injection rollback ở các write path. Lưu raw request/response đã che dữ liệu, DB before/after và actor/timestamp.

### QLK-5 — Thiết bị (QLK-UI-QA + H0; M)

`OFFLINE-NATIVE`, `PLATFORMS`: thiết bị mobile/tablet và Flutter web thật; ngắt mạng, kill/reopen, retry một lần, xác nhận không double-post; kiểm tra live API cùng SHA. Preview synthetic hiện tại chỉ là demo, không tính 2 ID này.

### CF-1a/1b/1c — 14 control trên Azure staging tổng hợp (CF; ba task M nối tiếp)

**1a — persistence:** bổ sung adapter bền vững cho revocation/session/work item và approved PostgreSQL/document storage adapter theo Clean Architecture. **1b — synthetic staging:** tạo ACA revision và frontend từ cùng SHA/digest, dữ liệu synthetic, OIDC test tenant riêng; không cấu hình mock IdP thành production. **1c — kiểm chứng:** chia 14 control thành `SEC-01..05 + PRIV-01`, `WF-01..05`, `MON-01..02 + SAFE-01`, chạy cloud E2E/negative controls/rollback. Kiểm chứng: full pytest, Gitleaks/Trivy/pip-audit, frontend build, role-scope controls, cloud E2E và rollback. API `:latest` cũ không được dùng làm release evidence.

### CF-2 — Tám gate ngân hàng (CF + H0; M mỗi contract)

`CF-G01` IdP/lifecycle; `G02` data rights/model validation; `G03` decision/core contract; `G04` privacy/security; `G05` DR; `G06` daily staff workflow; `G07` delayed outcomes; `G08` operational quality. AI chỉ làm contract, adapter, test và template bằng synthetic dữ liệu khi đầu vào ngân hàng chưa có. Gate chỉ PASS khi IAM/Data/Risk/Core/InfoSec/Operations/Business owner tương ứng cung cấp artifact, UAT và chữ ký. Không dùng dữ liệu tín dụng thật trước khi tất cả P0 được duyệt.

### REL-1 — Chốt phát hành và điểm (REL; S)

Sau mỗi batch 2–3 task, cập nhật ma trận theo ID, khóa SHA/digest/revision, liên kết raw log, CI và rollback. Tính `((AKS_PASS/14)+(QLK_PASS/21)+(CF_PASS/22))/3`; phải **>0,90**, không phải `>=`. Ghi riêng `go-live APPROVED/WAITING/REJECTED`, người ký, thời điểm và điều kiện còn mở. Không đưa mọi repo lên production chỉ vì portfolio vượt 90.

## Checkpoint và điều kiện bàn giao

1. **C0 — branch/secret:** H0 rotate token; CI xanh trên SHA mới; owner state/cost và UAT account được chỉ định. Các AI xác nhận worktree/file ownership.
2. **C1 — cloud nền:** AKS A13 có policy-toggle proof; QLK backend migration 034 + snapshot/rollback; CF synthetic ACA/frontend cùng SHA. Nếu thiếu một vế, giữ các cloud gate OPEN.
3. **C2 — nghiệp vụ:** QLK 21 log theo ID, thiết bị thật; CF 14 control cloud log và bank-owned gate artifacts. Chạy security/backup/restore và kiểm tra endpoint/revision sau deploy.
4. **C3 — release:** REL kiểm đếm PASS/OPEN/FAIL, CI, digest, cost, rollback và chữ ký go-live. Chỉ công bố “>90% có evidence” khi phép tính và truy vết cùng release đúng.

## Prompt ngắn để giao từng AI

> Bạn sở hữu gói **[ID]** trong `tasks/plan.md` của AKS-SRE-Platform. Đọc AGENTS.md của repo, ma trận gate và checkpoint nguồn. Làm trên worktree/branch riêng; không sửa file của AI khác. Thực hiện đúng phạm vi file, chạy lệnh verify ghi trong gói, tạo raw evidence UTC/SHA/digest/expected/actual, commit và trả `DONE/PARTIAL/BLOCKED` với PR/CI URL. Không đánh PASS nếu chưa có evidence đúng môi trường; không dùng secret đã lộ hoặc dữ liệu thật chưa được duyệt.

## Điểm cần người thật cung cấp

- Chủ tài khoản: token mới và GitHub Secrets, Azure state/cost/quota approval, môi trường cloud có rollback, tài khoản UAT/device.
- CreditFlow: tên chủ phê duyệt IAM, Data, Risk, Core Banking, InfoSec, Operations, Business và artifact tương ứng theo [`SACOMBANK_INPUTS_FOR_PILOT.md`](/Users/mainguyenbinhtan/Downloads/CreditFlow/docs/qa/SACOMBANK_INPUTS_FOR_PILOT.md).
- Đầu vào chưa có thì gate OPEN. Không gắn chữ ký thay người có thẩm quyền.
