# Kế hoạch thực thi 12 tuần — 4 repo, 3 vai trò Senior

**Đích tuyển dụng:** Senior Software Engineer, Software Architect, Senior DevOps/Platform Engineer. **Quỹ thời gian:** 20–30 giờ/tuần. **Nguyên tắc:** tối đa hai repo active, gate quyết định chuyển bước. Mọi bằng chứng dùng dữ liệu synthetic và nêu đúng môi trường. Kết quả của một phase là năng lực xử lý một rủi ro doanh nghiệp, không phải tổng số test.

## Bản đồ phase và chuyển cặp

| Phase / thời gian mục tiêu | Cặp active | Rủi ro doanh nghiệp phải giảm | Artifact phải bàn giao |
| --- | --- | --- | --- |
| 0 / đầu tuần 1 | Retail + Ops | Agent sau không biết code đang ở đâu, ghi đè WIP hoặc nhận nhầm CI cũ | STATUS sống, task owner, baseline SHA/CI, issue list có thứ tự |
| 1 / tuần 1–3 | Retail + Ops | Tiền bị ghi thiếu/trùng; flash sale bán quá tồn; CI/deploy cho tín hiệu sai | Retail atomic PR + Ops 50/10 dossier, CI/k6 trên exact SHA |
| 2 / tuần 4–6 | Retail + Quan | Outlet/chi nhánh xem hoặc sửa chéo; nhập/xuất/duyệt kho lệch sổ | Negative permission matrix, Retail ledger trace, Quan journey + migration proof |
| 3 / tuần 7–9 | Ops + AKS | Queue/retry làm mất đơn; bản release không triển khai/rollback lặp lại được | Fault matrix, immutable image, kind deploy/rollback Ops |
| 4 / tuần 10–11 | Quan + AKS | Platform chỉ chạy một app; migration/restore/alert chưa dùng được khi có sự cố | Cùng golden path cho Quan, alert/restore drill, cost report |
| 5 / tuần 12 | Mỗi lần một repo | Hồ sơ phỏng vấn có claim vượt bằng chứng hoặc thiếu câu chuyện kinh doanh | 3 case study, 3 CV focus, 5–10 phút demo/role, evidence index |

Nếu gate trễ: giữ correctness, quyền và CI; hoãn broker mới, UI/AI/ML mới và live cloud. Không có phase nào mặc nhiên cấp quyền apply/destroy Azure.

## Phase 0 — Baseline và hợp đồng AI coding

**Bài toán:** nhiều checkout và WIP làm AI dễ sửa sai branch, lấy badge cũ hoặc tạo việc trùng. **Invariant:** mỗi task có một owner và một SHA; WIP không bị mất; tối đa hai repo active.

- **File/owner:** hub AGENTS.md, STATUS.md, PHASES.md do integrator quản; repo owner giữ task/plan trong repo mình. Repo source thuộc từng workload/platform, không sửa từ hub.
- **Việc làm:** chụp Git branch/HEAD/status/remote/PR/CI; liệt kê WIP nào đang có owner, WIP nào orphan; đọc AGENTS/ADR; xác định một business scenario cho gate. Tạo issue/task chỉ có một kết quả đo được và một repo file owner.
- **Kiểm chứng:** link CI phải trỏ đúng SHA; diff/working tree không bị mất; review task có input, expected state, environment, gate và out-of-scope. Không lấy một CI cũ để đóng lỗi mới.
- **Output/gate:** STATUS cập nhật ngày/giờ; task đầu tiên của Retail/Ops sẵn sàng gửi AI. Không kích hoạt Quan hoặc AKS chỉ vì checkout có WIP.
- **Claim được phép:** “đã có baseline và quy trình bàn giao exact-SHA”; chưa claim reliability hay production.

## Phase 1 — Retail ledger và Ops sale baseline

### 1A. Retail Finance: account opening và giao dịch đúng

**Giá trị:** ngăn tài khoản mồ côi, mất bút toán mở đầu hoặc replay ghi tiền hai lần. **Invariant:** tạo account + bút toán CASH_IN đầu tiên + audit là một transaction; lỗi ở bất kỳ bước nào rollback toàn bộ; cùng idempotency key/cùng payload không double-post, khác payload phải conflict.

- **Owner/code:** Retail backend AccountController/AccountOpeningService, TransactionService, AuditService, repository và migration nếu cần; test dưới backend/src/test/java. Python reconciliation-service vẫn là consumer/đối soát, không được điều khiển ledger.
- **Tái hiện trước sửa:** inject lỗi sau account insert/trước posting hoặc audit, query MySQL để thấy orphan account hoặc mất audit; thử concurrent duplicate/replay. Lưu RED output và trạng thái DB, không chỉ exception.
- **Sửa và chứng minh:** transaction boundary rõ; unique constraint xử lý đúng loại xung đột; Testcontainers MySQL kiểm tra account, transaction, balance, audit trước/sau fail; Java unit/integration + Python recon pass; CodeQL và CI trên commit của PR. Với migration chạy DB mới và DB phiên bản trước, ghi cách forward-fix.
- **Output/gate:** PR nhỏ, ADR nêu lựa chọn atomic DB so với saga/queue, raw query/test logs, exact SHA/CI URL. Reviewer correctness độc lập kiểm tra diff cuối, nhất là exception translation.
- **Claim:** “đã chứng minh account opening atomic và replay không double-post trên MySQL integration test tại SHA X”; không claim hệ thống giao dịch production.

### 1B. OpsBridge/FlashSale: 50 người tranh 10 suất

**Giá trị:** doanh nghiệp không oversell và có thể giải thích vì sao khách bị từ chối. **Invariant:** 50 yêu cầu đồng thời trên tồn 10 tạo đúng 10 accepted durable orders, 40 business rejections, stock cuối 0; không âm tồn hoặc duplicate order. HTTP success, k6 threshold và DB invariant là ba phép đo khác nhau.

- **Owner/code:** FlashSale.Application/Orders, FlashSale.Infrastructure/Persistence/Redis/Messaging, Order.Api, Order.Worker; harness ở load-tests/concurrency và k6; CI ở .github/workflows/ci.yml và load-test.yml. OpsBridge.Api/.Web là bounded context riêng, không ghi chéo DB FlashSale.
- **Tái hiện/chứng minh:** reset DB/Redis synthetic theo recipe; chạy concurrency harness có barrier; lưu request IDs/status, DB order count/state, inventory row, Redis state và thời gian. Chạy k6 profile riêng, lưu virtual users/duration/p95/error; tách business reject 409 khỏi lỗi kỹ thuật. Main CI và k6 đã xanh ở ef1f827; 50/10 DB proof vẫn cần thu thập riêng.
- **Output/gate:** dossier tái chạy được, artifact raw + script + container version + exact SHA; README chỉ nêu con số thực đo. Release chỉ khi CI gate pass và workflow manual promotion.
- **Claim:** “50 yêu cầu synthetic tranh 10 suất tại SHA X: 10 durable orders, 40 reject, stock 0 trên môi trường Y” sau khi DB proof có thật. Không nói throughput/SLA production từ local runner.

**Điểm dừng Phase 1:** Retail atomic được independent review và CI, Ops 50/10 được DB proof trên SHA xác định. Nếu thiếu một bên, ghi PARTIAL/NOT_VERIFIED; không kích hoạt repo thứ ba.

## Phase 2 — Quyền dữ liệu và hành trình kho

### 2A. Retail: outlet/identity/PII

**Giá trị:** POS outlet A không được đọc, ghi hoặc replay request cho outlet B; audit và đối soát có người chịu trách nhiệm. **Invariant:** authorization theo object tại service/query boundary, không chỉ route/JWT role; replay không bypass scope; national ID/secrets không xuất hiện trong log hoặc secret mặc định ở môi trường không-local.

- **Owner/code:** Retail security/Jwt*, SecurityConfig, Account/Transaction/AuditController và service/repository query; backend integration tests, config/migration và reconciliation-service auth/report nếu thay đổi.
- **Tái hiện:** token outlet A dùng account/transaction ID outlet B trên GET, POST và idempotency replay; assert deny và DB/audit không đổi. Tạo matrix actor × outlet × operation (POS, reviewer, admin) và test đúng policy. Kiểm tra negative secret startup và PII masking bằng dữ liệu synthetic.
- **Output/gate:** threat model, ADR PII lựa chọn/migration, audit record có actor, schema upgrade proof và exact-SHA CI. Trước dữ liệu thật, review thiết kế bảo vệ PII và secret rotation.
- **Claim:** “object-level outlet isolation qua HTTP + MySQL tests”; không nói compliance certification hoặc dữ liệu khách hàng thật.

### 2B. QuanLyKho: canonical workflow và branch scope

**Giá trị:** nhập nguyên liệu theo lô/HSD, xuất FEFO, kiểm kê và maker–checker tạo số tồn tin cậy; nhân viên không thể sửa kho chi nhánh khác; AI không thể duyệt thay người. **Invariant:** inventory movement/balance/audit/outbox đồng bộ; mỗi approval chỉ post một lần; reviewer chỉ đọc phạm vi được cấp; AI assessment cần phiếu canonical và chỉ tư vấn.

- **Owner/code:** backend/app/api/routes/inventory.py, approvals/demo/AI routes, service/model/migration liên quan; backend/tests/test_inventory_alert_scope_unit.py, test_reviewer_readonly.py, test_ai_assessment_canonical.py, test_phase3_business_journey.py; .github/workflows/ci.yml. Giữ Flutter là client; Cloudflare Worker legacy ngoài đường ghi chuẩn.
- **R0 trước R1:** bảo toàn WIP main và QuanLyKho-R0, xác định owner; sửa CI theo contract hiện hành (AI ID canonical, pagination, reviewer capability, demo profile, env template, S11 DAG) bằng failing reproduction. Chạy Ruff/Poetry/Pytest và CI/S10/S11/GitOps trên cùng SHA; deploy Azure là gate riêng.
- **Journey:** DB synthetic cô lập: nhận lô có HSD → xuất FEFO → kiểm kê lệch → submit → checker approve/reject. Sau mỗi bước query movement, balance, audit, outbox; negative tests branch/location, hai checker đồng thời, idempotency replay, worker crash sau commit. Không chỉ assert HTTP 200.
- **Migration/recovery:** Alembic DB mới và upgrade từ bản cũ, backup/restore DB tách biệt; đo RTO/RPO của drill thay vì lặp mục tiêu runbook. Một load profile theo ca vận hành với p95/error và correctness dưới tải.
- **Output/gate:** CI xanh trên SHA mới + raw journey trace + negative matrix + migration/restore artifact. Tài liệu không gọi cash-sim là core banking.
- **Claim:** “đã kiểm chứng journey nhập/FEFO/kiểm kê/phê duyệt và branch isolation trên PostgreSQL synthetic”; không claim vận hành kho khách hàng thật.

**Điểm dừng Phase 2:** Retail account+outlet proof và Quan R0/journey proof có SHA/CI. Nếu Quan CI đỏ, cắt AI/ML/UI trước; không cắt quyền branch hoặc dữ liệu tồn.

## Phase 3 — Fault recovery và platform workload thứ nhất

### 3A. Ops: xử lý sự kiện at-least-once

**Giá trị:** broker chậm/lỗi hoặc worker restart không làm mất đơn, giữ Redis reserve vĩnh viễn hay xử lý đơn hai lần. **Invariant:** PostgreSQL là stock/order truth; reserve/queue/commit có compensation rõ; duplicate delivery idempotent; trạng thái terminal có thể đối soát.

- **Owner/code:** FlashSale.Application/Orders, Infrastructure/Messaging, Persistence, Redis, integration tests/compose và load-tests; OpsBridge contract riêng nếu gửi sự kiện qua bounded context.
- **Fault matrix tối thiểu:** queue reject sau Redis reserve; broker nack/mất kết nối trước ACK; worker crash sau DB commit trước ACK; duplicate message/webhook cùng và khác payload. Với từng ca lưu request, DB/Redis/queue trước-sau, DLQ/retry, recovery time. Không mô phỏng toàn bộ bằng mock.
- **ADR:** so sánh giữ PostgreSQL transaction/outbox với thêm Kafka/RabbitMQ/Redis; chỉ dùng broker khi consumer/replay/failure model rõ. Không thêm Kafka để đủ stack. Không hứa exactly-once transport.
- **Output/gate:** fault drill script + raw logs/trace + DB query + on-call runbook + CI integration trên exact SHA. Benchmark phải có baseline/limits.
- **Claim:** “đã phục hồi đúng những lỗi broker/worker đã tiêm trong môi trường Y”; không nói chịu mọi lỗi phân tán.

### 3B. AKS: golden path đầu tiên trên kind

**Giá trị:** team phát hành app theo một hợp đồng lặp lại thay vì thao tác cá nhân, biết rollback khi release xấu. **Invariant:** cloud apply không chạy khi push; image immutable digest; migration chạy/được kiểm tra trước rollout; Argo theo release ref thật; health/policy gate chặn release lỗi.

- **Owner workload:** Ops repo build/publish Order.Api/Worker và OpsBridge.Api/.Web cần dùng, image digest, overlay, migration Job, probes, business metrics. Canonical CI hiện chưa publish OpsBridge.Api/.Web: phải bổ sung trước khi claim OpsBridge workload deployed.
- **Owner platform:** AKS repo .github/workflows/aks-deploy.yml, terraform/aks-foundation + state, scripts/bootstrap.sh, platform/argocd, namespace/AppProject/policy/gateway/observability, tests/test_gates.py. Không kéo business logic vào platform.
- **Safety gate trước cloud:** read-only xác minh Terraform remote state owner/key, subscription, OIDC federated identity, quota/budget và saved plan. Thay auto apply trên push và bootstrap path máy cá nhân bằng workflow thủ công có environment approval. Không điền client secret lâu hạn để làm workflow xanh.
- **Kind proof:** PR → CI → image digest → migration on clean/upgrade DB → Kustomize render/source ref → Argo sync → probe → fault/rollback. Test policy negative (floating tag, missing limit/non-root, namespace violation). Ghi SHA của cả workload và platform, digest, command, Argo revision, trước/sau rollback.
- **Output/gate:** một golden path Ops trên kind; cloud apply tách gate. Khi OIDC/state/budget chưa đủ, trạng thái Azure là NOT_VERIFIED.
- **Claim:** “đã triển khai và rollback Ops qua golden path trên kind”; không gọi kind là AKS runtime.

**Điểm dừng Phase 3:** fault matrix có durable state; kind release/rollback bằng digest trên exact source refs. Azure chỉ sau safety gate và human approval.

## Phase 4 — Workload thứ hai, SRE và FinOps

**Giá trị:** platform có ích khi dùng lại cho QuanLyKho, sự cố có alert có thể hành động và restore đo được; cloud demo không tiêu tiền vô kiểm soát. **Invariant:** hai workload theo cùng contract nhưng mỗi repo sở hữu app riêng; alert fire/resolve; restore ra DB cô lập; state và cost được ghi.

- **Owner Quan:** image/Dockerfile, infra/k8s overlay release, Alembic migration Job, readiness/liveness, business metrics; tránh staging-latest/hostname placeholder ở release.
- **Owner AKS:** Argo Application/AppProject/namespace/route/policy, repo-map validator, observability, backup/DR, cost guardrails. Render đúng ref của cả Ops và Quan; validator phải fail khi checkout/ref hoặc digest thiếu.
- **SRE scenario:** chọn một SLI kỹ thuật (success/latency) và một SLI nghiệp vụ cho mỗi workload (đơn bền vững/approval posting). Viết target và burn/alert theo dữ liệu đo, test fire/resolve, runbook điều tra. Drill pod/worker mất, Argo drift, policy deny, DB restore; ghi detection, timeline, RTO/RPO thực, data loss và giới hạn.
- **FinOps/cloud gate:** budget alert, tags, quota, schedule stop/start, teardown và restart verification; chi phí lần chạy thực. Chỉ chạy AKS khi identity/state/approval đầy đủ. Live Azure evidence phải gồm ACR pull, Argo sync, health, rollback/restore và billing; nếu không, giữ KIND_VERIFIED/NOT_VERIFIED.
- **Output/gate:** cùng một golden path cho hai app, raw alert/restore evidence và cost report. Policy-as-code có positive + negative fixtures, SBOM/scan/provenance gắn digest.
- **Claim:** “hai workload tái dùng release path trên kind, alert và restore drill đo được”; chỉ thêm “trên AKS” khi đã chạy AKS thật.

## Phase 5 — Multi-agent automation và hồ sơ tuyển dụng

**Agent nghiệp vụ:** Retail reconciliation triage và Quan inventory ops chỉ đọc dữ liệu có quyền, xuất structured evidence/proposal; người có quyền duyệt. Chỉ thêm AI/LLM sau khi access control, persisted run, redaction và eval trên ca synthetic đạt gate. Agent không tự post ledger, approve stock hay rollback infra.

**Agent kỹ thuật:** correctness, platform, architecture reviewer đọc PR/CI/ADR độc lập; một integrator sửa file và merge. Scheduled agent chỉ báo thay đổi actionable có SHA, URL và severity; không tự coi badge xanh là release. Incident agent chỉ triage read-only; human duyệt action cloud/order/ledger.

**Ba case study bắt buộc:**

1. Retail: “Retry không ghi tiền hai lần” — trước/sau DB, failure injection, transaction boundary, quyền outlet, trade-off.
2. Ops: “50 khách tranh 10 suất, broker lỗi vẫn phục hồi” — 10/40/0, durable orders, fault matrix, p95/error theo môi trường.
3. AKS + Quan: “Hai workload dùng một golden path” — digest, migrations, Argo, policy, rollback, alert, restore, cost.

Mỗi case có bối cảnh doanh nghiệp, lựa chọn thiết kế, phương án bỏ qua, raw measurement, SHA/CI, giới hạn còn lại và một demo 5–10 phút. CV Java mở bằng Retail; Architect mở bằng transaction/bounded contexts/trade-offs; Platform mở bằng state safety/OIDC/GitOps/SLO/recovery. Portfolio là bằng chứng kỹ thuật; kinh nghiệm production ở công ty phải khai trung thực riêng.

**Gate cuối:** mọi câu trong README/CV trỏ tới evidence index có SHA, URL hoặc artifact local; claim không có proof chuyển thành DESIGN_ONLY/NOT_VERIFIED. Ba người review khác nhau có thể kiểm tra correctness, architecture, platform; integrator chịu trách nhiệm câu chữ cuối.

## Template giao việc cho AI kế tiếp

Sao chép và điền template này vào một task. Chỉ giao một kết quả trong một repo cho một agent sửa code.

> **Phase/gate:** …
>
> **Repo, checkout/branch/HEAD/remote main:** …
>
> **Business problem và người dùng chịu ảnh hưởng:** …
>
> **Invariant phải giữ, failure mode cần tái hiện:** …
>
> **File owner / phạm vi được sửa:** … (mọi agent khác review read-only; không ghi đè WIP)
>
> **Baseline evidence:** CI URL + SHA, test/log/DB hiện có, trạng thái NOT_VERIFIED …
>
> **TDD/reproduction:** lệnh chạy trước sửa và expected RED/data trước-sau …
>
> **Thay đổi nhỏ nhất:** …; ADR nếu đổi transaction boundary/contract/infra
>
> **Verify/gate:** lệnh thực, DB/queue query, negative case, CI exact SHA, raw artifact, environment …
>
> **Allowed claim:** …; **forbidden claim:** …
>
> **Stop/go:** dừng nếu invariant còn fail, CI khác SHA, migration/rollback chưa có proof, thiếu state/OIDC/budget cho cloud, hoặc WIP owner chưa rõ. Báo BLOCKED với evidence và đầu vào thiếu; không bỏ test/gate để lấy màu xanh.

## Sổ bằng chứng cho mỗi case

Đặt trong repo sở hữu case hoặc một index ở hub (không chép secret/PII): ngày giờ, Git SHA và branch, PR/CI run URL, image digest, môi trường và phiên bản DB/broker, dữ liệu synthetic seed, command, stdout/artifact raw, DB before/after, metrics tải p95/error, fault injection, rollback/restore timeline và giới hạn. Kết luận phải suy ra được từ artifact; không gán production SLO cho local/kind.
