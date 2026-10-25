# Hợp đồng giao việc Antigravity: hoàn tất bốn repo và Agent Hub theo gate thực tế

**Ngày lập:** 2026-10-24. **Trạng thái:** PLAN, chưa chứng nhận triển khai. **Mục tiêu:** bốn repo chứng minh được năng lực Senior SWE, Software Architect và Senior DevOps/Platform bằng dữ liệu, quyền truy cập, failure recovery và release path có thể tái hiện. Agent Hub chỉ hỗ trợ điều tra read-only khi tạo giá trị đo được.

## 0. Quy tắc không cho AI đoán

1. Đọc `AGENTS.md`, `PHASES.md`, `STATUS.md`, AGENTS/ADR trong repo sở hữu task. Chụp `git status`, HEAD, remote main, PR và CI live. `STATUS.md` chỉ là snapshot. Nếu có `.codegraph/` ở repo root, dùng CodeGraph trước `rg`/đọc code. Không ghi đè WIP hoặc tự sửa đồng thời cùng file với agent khác.
2. Tối đa **hai thành phần active**; reviewer khác chỉ đọc. Một integrator duy nhất sửa/merge. Mỗi task có một owner repo, danh sách file được sửa, test RED trước, lệnh GREEN sau và artifact raw.
3. Gắn nhãn mọi dependency/API: `EXISTS` kèm path và chữ ký đang có, `NEW CONTRACT` kèm ADR + OpenAPI + test consumer/provider, hoặc `UNKNOWN` và **dừng** để khảo sát. Không tự bịa endpoint, header, role, DB schema, alert, SHA hoặc dữ liệu.
4. `httpx.MockTransport`, fixture synthetic và 200 `/healthz` chỉ chứng minh unit/smoke. Gate tích hợp yêu cầu service thật trên môi trường cô lập, DB/broker thật khi ca cần chúng, kiểm tra dữ liệu trước/sau và quyền tại service sở hữu dữ liệu.
5. Không sửa test để hợp thức hóa implementation. Khi phát hiện test sai, giữ reproduction và giải thích vì sao test cũ không đo được invariant, rồi thêm case độc lập. Không dùng `or abstained` để bỏ qua verdict, không tạo input từ expected verdict.
6. Không đưa secret vào code/browser/PR/log. Không dùng token mẫu cho môi trường ngoài test. Không tạo quyền ghi ledger/order/stock/cloud cho Hub. Cloud `apply/destroy` theo environment approval, saved plan và state owner đã kiểm tra.
7. Mỗi phase báo `DONE/PARTIAL/BLOCKED` kèm exact SHA, CI URL, lệnh/output, môi trường, dữ liệu synthetic hay thật, giới hạn claim. Nếu không có đủ bằng chứng, ghi `NOT_VERIFIED` và dừng phase tiếp theo.

## 1. Baseline phải chụp lại, không mặc định đã đạt

Tại lần audit gần nhất, Retail CI + CodeQL xanh ở `433447f`, Ops CI + k6 xanh ở `b507464`, Quan CI xanh ở `1bb494a` nhưng deploy Azure thất bại tại Azure Login, AKS GitOps validate xanh nhưng OIDC live âm tính và apply/Bootstrap Argo thất bại. Kind có `flashsale` và `quanlykho` Synced/Healthy; đó là bằng chứng Kind, không phải cloud. Hub đang ở working tree chưa commit; code và test bị sửa đồng thời. Lần chạy local gần nhất có **6 fail, 16 pass** do auth JWT mới không khớp test token mẫu. Antigravity phải chạy lại, không lấy số này làm trạng thái vĩnh viễn.

**Nguồn đối chiếu:**

- Retail `GET /api/v1/transactions/settled` thực tế bắt buộc `from`, `to`, có `limit`, `page`, yêu cầu `ROLE_OPS`: `services/retail-finance/backend/src/main/java/com/mtaretail/core/web/TransactionController.java` và `.../config/SecurityConfig.java`. Endpoint này trả feed toàn outlet cho OPS; lọc ở Hub sau khi nhận **không phải** cô lập dữ liệu tại nguồn.
- Retail recon có logic đọc feed phân trang và đối chiếu CSV ở `services/retail-finance/reconciliation-service/app/main.py`, `app/reconciler.py`, `app/triage.py`. MySQL ledger là nguồn sự thật; Hub không tạo transaction.
- Ops GET result/discrepancies/batches/audit-trail ở `services/opsbridge-flashsale/src/OpsBridge.Api/Endpoints/ReconciliationEndpoints.cs`, GET outbox ở `src/Order.Api/Program.cs`. POST reconcile/review/requeue là mutation và không thành Hub tool.
- Quan `POST /api/v1/ai/assess-request` ở `services/quanlykho/backend/app/api/routes/ai.py` đọc phiếu canonical, kiểm tra location và trả advisory; maker–checker/commit nằm ở `routes/inventory.py`. Không gọi approve/post từ Hub.
- AKS `scripts/aiops_incident_triage.py` là CLI keyword matcher, không có receiver bền vững. Kind Alertmanager từng tắt; Langfuse manifest không chứng minh trace/eval.
- Hub hiện có `services/agent-hub/app/auth.py`, `core/storage.py`, `core/run_manager.py`, bốn adapter và test. Đây là implementation WIP, không phải chuẩn để sao chép mà không kiểm chứng.

**Output Gate 0:** một bảng `repo → branch/HEAD/remote main → dirty files/owner → CI runs → môi trường → trạng thái từng gate`; ADR cho identity/data-flow; contract tool với từng endpoint `EXISTS/NEW/UNKNOWN`; 12–16 casebook có dữ liệu seed và verdict độc lập. Nếu owner WIP không rõ, dừng code, báo blocker.

## 2. Thứ tự và giới hạn active

| Gate | Active tối đa | Vì sao theo thứ tự này | Điều kiện chuyển |
| --- | --- | --- | --- |
| G0 | Chỉ tài liệu/khảo sát | Chặn sai branch/API/WIP. | Owner, contract, casebook và baseline được ghi. |
| G1 | Agent Hub + Retail | Đóng auth/state trước khi đọc tài chính. | Security negative và Retail canonical integration xanh. |
| G2 | Agent Hub + Ops | Dùng case queue/order thật và UI có quyền. | Fault matrix, DB invariant và frontend route có chứng cứ. |
| G3 | Agent Hub + Quan | Dùng phiếu canonical, quyền chi nhánh, maker–checker. | Eval answer/citation và negative scope/stale xanh. |
| G4a | Quan + AKS | Đóng release của workload thứ hai trên Kind rồi Azure. Hub tạm đóng băng. | Hai workload cùng golden path ở môi trường được claim. |
| G4b | Agent Hub + AKS | Incident receiver/correlation và deploy Hub. | Alert fire/resolve, audit, rollback/restore có raw timeline. |
| G5 | Từng repo một | Hồ sơ/case study chỉ theo bằng chứng đã đạt. | Reviewer độc lập tái hiện được claim. |

## 3. G1a — Khóa identity, dữ liệu và run state của Agent Hub

**Business risk:** người không có quyền đọc hồ sơ outlet/branch hoặc mạo danh người duyệt; run mất hoặc trùng sau retry. **Owner:** `services/agent-hub/app/auth.py`, `app/main.py`, `core/storage.py`, `core/run_manager.py`, migrations mới và targeted tests. Không sửa Retail trong subtask G1a.

**RED trước code:** unsigned/forged/wrong-alg/wrong-issuer/wrong-audience/expired JWT; token HN đọc run SG; client đặt `reviewer_id`; hai caller khác scope dùng cùng `X-Idempotency-Key`; cùng key nhưng payload khác; hai request song song; pod restart giữa `evidence_collected` và `proposed`; quyết định ghi hai lần. Lưu input và HTTP status/DB rows trước sửa.

**Thay đổi bắt buộc:**

- Auth fail closed khi thiếu secret/cấu hình issuer, audience; không có HMAC secret mặc định trong source hay token hardcode ở browser. Xác định issuer đang dùng thực tế hoặc triển khai identity provider đã duyệt. Nếu chưa có issuer, chỉ chạy test/local, không mở route cho người dùng. Verify chữ ký, `alg` allowlist, `iss`, `aud`, `exp`, `nbf` nếu có, subject/role/scope và key rotation. Không tự tạo token bằng cùng secret production trong Hub cho client.
- Mọi API lấy identity từ token đã verify; domain service kiểm tra scope lại. Decision chỉ cho role đúng theo case, trạng thái hợp lệ và người khác maker khi nghiệp vụ yêu cầu. Không trả full `proposal_json` chứa dữ liệu khác scope.
- Idempotency key phải bind với `caller_id + scope_id + case_type + entity_ref + request_hash`, và lưu trong transaction có unique constraint; cùng key/cùng payload trả cùng run, key khác payload trả 409, cross-scope không trả proposal cũ. Không `INSERT OR REPLACE` run/evidence. Xử lý cạnh tranh bằng transaction/constraint thay vì check-then-insert đơn thuần.
- Run store riêng của Hub có migration, backup/restore và retention. PVC SQLite một replica chỉ đủ cho Kind demo; nếu chọn PostgreSQL cho release, dùng DB riêng, không tái sử dụng schema/credentials của FlashSale. Ghi state transition hợp lệ và recovery từ run dở. Hash facts là checksum, không gọi là chữ ký số/authenticity.
- `synthetic_payload` chỉ có ở test factory không thể bật trên deployment release bằng một env flag sai. Reject/strip dữ liệu PII trước persistence/trace và provider; không log raw secret.

**Gate:** chạy targeted auth/idempotency test với DB thật, song song và crash/restart; 0 truy cập sai scope, 0 mất/chồng quyết định, 0 token mẫu/secret trong build frontend/image. `pytest` toàn suite Hub xanh trên cùng SHA. Ghi rõ `KIND_SECURITY_VERIFIED`; chưa claim production.

## 4. G1b — Retail Finance: đối soát đúng và quyền ngay tại nguồn

**Business risk:** báo thiếu tiền giả, bỏ sót mismatch, hoặc Hub nhận feed toàn outlet rồi lọc ở client. **Owner:** Retail backend/recon (endpoint/domain auth) và Retail adapter của Hub; mỗi task một owner file, không sửa cùng lúc. **Invariant:** MySQL ledger không đổi bởi Hub; partner và settled feed có nguồn, thời gian, currency/amount/reference; không đọc outlet khác.

**Contract hiện có:** Java `GET /api/v1/transactions/settled?from=&to=&limit=&page=` trả `List<TransactionResponse>` và yêu cầu `ROLE_OPS`. Hub WIP đang đọc chỉ `page=0`, lọc `outletCode` sau khi đã lấy feed toàn outlet và tự điền SHA/version mặc định. Đây **chưa** là contract scoped hợp lệ.

**Task Retail owner:** viết ADR + OpenAPI cho `NEW CONTRACT` đọc settled feed có outlet scope được **Java xác minh trước query**, phân trang đầy đủ, window bound, response version/provenance thật. Thiết kế token service/delegation dựa trên `JwtAuthenticationFilter`/quyền hiện hữu; tuyệt đối không tin `X-Outlet-Scope` nếu token không ràng buộc. Nếu không có cơ chế cấp identity đáng tin, dừng G1b và nêu dependency. Giữ endpoint OPS cũ nếu cần tương thích, thêm endpoint/version mới sau contract test; không lặng lẽ nới quyền OPS.

**Task Hub owner sau khi provider contract xanh:** gọi endpoint đã ký, dùng URL nội bộ/service DNS thật, fail closed khi timeout/403/5xx/truncated page/missing version, không fallback thành `MISSING_LEDGER`; fetch hết page trong giới hạn, nối partner feed có provenance, so exact reference/amount/currency bằng logic recon hiện hữu. Không suy nguyên nhân “phí gateway” khi không có evidence. Không lưu raw tài khoản/PII vào facts/trace.

**RED và gate:** case thiếu ở partner, thiếu ở ledger, duplicate, amount mismatch, outlet khác, feed page 2, race settlement sau snapshot, 403/timeout. Chạy Java/MySQL Testcontainers và recon integration **không dùng MockTransport cho gate**; kiểm DB before/after = không có write bởi Hub; cùng case có citation record ID/version và từ chối stale. `MockTransport` chỉ giữ ở unit test. Báo thời gian analyst so với baseline, false-safe và cost/case. Chỉ claim “Retail case integration” khi provider + consumer cùng SHA/CI và service thật được chạy.

## 5. G2 — OpsBridge/FlashSale: queue/order và UI có quyền

**Business risk:** báo đơn đã bán khi reservation/outbox/queue chưa khôi phục; nhân viên nhìn hóa đơn hardcode như dữ liệu thật. **Owner:** Ops API/Web và Ops adapter Hub; Hub + Ops active. **Invariant:** PostgreSQL quyết định order/stock; at-least-once có thể lặp; Hub không POST reconcile/review/requeue.

**Task:** map API `EXISTS` (GET reconciliation result/discrepancies/batches/audit-trail, GET outbox). Nếu order timeline thiếu, ghi `NEW CONTRACT` read-only với `order_id`, record version, event IDs, state từ Postgres/broker và quyền Auditor/SRE. Adapter chỉ trả facts lấy từ API và nguồn có ID, không default `RESERVED/ACKED` hoặc SHA hardcode. UI gửi entity ID được chọn từ bảng thật; không dùng free-text 50 ký tự làm order ID, không gắn bearer token trong bundle. Kết nối browser → BFF đã xác thực → Hub; Vite proxy chỉ cho dev, cần route production tương ứng. Nếu Hub lỗi, UI ghi “chưa có dữ liệu”, không trả số invoice/khuyến nghị giả.

**RED và gate:** 50 requests/10 units qua API và PostgreSQL (đúng 10 order durable, 40 reject, stock 0); queue reject sau reserve, mất ACK, worker crash sau commit, duplicate delivery, outbox stuck. Agent chỉ kết luận theo DB/queue trước/sau; error/unknown phải abstain. Test âm tính Auditor không gọi được mutation; browser test Network tab/bundle không có token/provider key, production routing trả đúng Hub auth response. CI/k6 xanh trên SHA triển khai; số liệu latency ghi môi trường/tải. Không gọi “AI xử lý đơn” vì không có write action.

## 6. G3 — QuanLyKho: hỗ trợ checker trên phiếu canonical

**Business risk:** AI đề xuất duyệt phiếu sai lô hoặc lộ dữ liệu chi nhánh; reviewer hiểu nhầm đề xuất là approval. **Owner:** Quan backend/UI và Quan adapter Hub; Hub + Quan active. **Invariant:** maker ≠ checker, branch scope ở DB query, risk floor deterministic, AI không approve/post.

**Contract `EXISTS`:** `POST /api/v1/ai/assess-request` nạp phiếu từ DB và kiểm location; route approval trong `inventory.py` giữ khóa dòng, quyền và audit/outbox. Đây là read/advisory computation dù dùng HTTP POST; kiểm tra side effect trước khi đăng ký tool. Hub không gọi các route approve/post.

**Task:** adapter gọi API canonical với identity/service scope hợp lệ; giữ voucher ID + record version + branch + lô/expiry/quantity + SOP citation. Bỏ client override model provider, redaction trace, rate limit dùng chung khi nhiều replica; eval generated answer và citation, runner exit nonzero khi fail. Nếu MLflow promotion được đưa vào case, thiếu R² phải fail closed và synthetic training phải gắn nhãn synthetic.

**RED và gate:** cross-branch 404/403 ngay tại Quan; maker tự duyệt; voucher đổi version sau fetch; FEFO lô sớm còn tồn; provider timeout/risk thấp; SOP prompt injection. Phải thấy DB state/audit/outbox không đổi bởi Hub; checker quyết định qua UI riêng. Báo false-negative high-risk, citation validity và thời gian kiểm phiếu so baseline. Không gọi “tự động duyệt kho”.

## 7. G4a — Quan + AKS: hoàn tất delivery cloud cho hai workload

**Business risk:** CI xanh/Kind healthy nhưng deploy Azure đỏ hoặc app trên AKS `OutOfSync/Missing`. **Owner:** Quan image/migration/probes/business metrics; AKS state/OIDC/Argo/policy/observability/cost. Hub không active trong gate này.

**Baseline live cần kiểm lại:** Quan `Deploy QuanLyKho API` thất bại ở Azure Login (OIDC); AKS `oidc-azure` negative control fail; lần `AKS Deploy` apply gần nhất fail ở Bootstrap Argo CD. Một workflow `AKS Deploy` ghi success nhưng Apply job skipped không chứng minh deploy. Tài liệu cloud ghi cluster tồn tại, Argo pods Ready, nhưng `flashsale` và `quanlykho` `OutOfSync/Missing`; không được gọi golden path cloud xong.

**Task:** xác minh Terraform state owner, OIDC subject/environment positive + negative, quota/budget và reviewed saved plan; sửa nguyên nhân workflow từ log thật. Quan build image digest, Alembic migration Job trước rollout, probes; AKS Argo AppProject/Application source ref và namespace/route/policy. Chạy cả FlashSale và Quan trên AKS với digest thật, Argo Synced/Healthy, external route, log migration, policy deny, rollback và backup/restore có order/phiếu delta. Ghi chi phí run. Cloud apply/destroy chỉ manual approval.

**Gate:** exact SHA CI của cả canonical repo, image digest, plan artifact, reviewer environment, `kubectl`/Argo/HTTP raw output trên context AKS (ghi context), fault/restore timeline và business data before/after. Nếu một workload còn Missing hoặc deploy/OIDC đỏ, giữ `CLOUD_PARTIAL`; Kind proof vẫn riêng `KIND_VERIFIED`.

## 8. G4b — Hub + AKS: incident correlation có ích cho on-call

**Business risk:** alert nhiều nguồn làm chậm tìm root cause; agent diễn giải runbook thành lệnh nguy hiểm. **Owner:** AKS alert receiver/telemetry/runbook và Hub incident adapter. **Invariant:** Hub chỉ đọc alert, Argo, CI và metric; không có credential `kubectl apply`, Terraform, Argo sync/rollback.

**Task:** xây receiver xác thực, dedup fingerprint, run store; kết nối Alertmanager/Prometheus và Argo **thật** bằng read-only service identity. Một case xuyên repo bắt buộc: alert worker/error → Ops order/outbox + AKS rollout timeline → đề xuất bước xác minh có source ID/SHA/image. Runbook là input không đáng tin; output không chứa executable command. Tạo dashboard latency/error/abstain/cost và runbook human-operated. Triển khai Hub bằng image digest, migration/probes/policy, không `:local` cho cloud.

**RED và gate:** forged/replayed alert, duplicate alert, stale metric, rollout lỗi, runbook prompt injection, provider timeout; alert fire → receiver → triage → con người quyết định → verify → resolve với raw timestamp. On-call đo thời gian tìm nguyên nhân trước/sau cùng case; nếu không cải thiện lặp lại hoặc false-safe tăng, tắt LLM synthesis và giữ evidence aggregator/rules.

## 9. G5 — Acceptance, claim và hồ sơ tuyển dụng

**Acceptance cho từng repo:**

| Repo | Claim được phép sau gate | Claim chưa được phép nếu thiếu proof |
| --- | --- | --- |
| Retail | MySQL transaction/outlet/reconciliation invariant với CI + integration exact SHA; agent read-only trên feed scoped thật. | “Production banking/zero financial loss/AI tự sửa ledger”. |
| Ops | 50/10, broker fault recovery và timeline DB/queue, CI+k6 cùng SHA; UI gọi Hub có quyền. | “Order tự phục hồi nhờ LLM” hoặc số KPI không đo. |
| Quan | FEFO, maker–checker, branch isolation, phiếu canonical advisory và eval faithfulness; deployment theo môi trường thật. | “AI tự duyệt/ML dự báo chính xác trên dữ liệu doanh nghiệp” khi chỉ có synthetic. |
| AKS | Hai workload cùng golden path ở Kind hoặc AKS **ghi rõ nơi chạy**, OIDC/Argo/rollback/restore/cost raw evidence. | “Cloud production-ready” nếu workflow đỏ, app Missing hoặc chỉ có Kind. |

Một reviewer correctness, một reviewer security/platform, một reviewer architecture đọc PR/CI/ADR/evidence; integrator xử lý findings. Ba case study phỏng vấn: (1) Retail retry không double post, (2) Ops 50/10 khi broker lỗi, (3) hai workload deploy/rollback/DR theo golden path. AI case study riêng chỉ khi human pilot có baseline và cải thiện. README/CV chỉ trỏ bằng chứng exact SHA và ghi rõ synthetic/local/Kind/AKS.

## 10. Mẫu prompt gửi Antigravity cho từng phase

> Hãy thực thi **chỉ gate tiếp theo chưa đạt** trong `docs/plans/antigravity-four-repo-execution-contract.md`. Trước khi sửa, đọc `AGENTS.md`, `PHASES.md`, `STATUS.md` và AGENTS/ADR của repo sở hữu task; chụp Git/CI/cluster live, xác định WIP/owner. Liệt kê API `EXISTS`, `NEW CONTRACT`, `UNKNOWN` với path/chữ ký; nếu `UNKNOWN`, dừng để khảo sát, không bịa. Đưa một reproduction RED và business invariant, nêu file owner, rồi làm thay đổi nhỏ nhất. Chạy integration với service/DB/broker thật theo gate, negative security, fault recovery, CI exact SHA; lưu raw output và dữ liệu before/after. Không sửa test cho xanh bằng cách nới invariant, không ghi secret/PII, không tự thao tác cloud hoặc nghiệp vụ ghi mà thiếu human approval. Kết thúc bằng `DONE/PARTIAL/BLOCKED`, claim được phép, claim chưa được phép và task tiếp theo. Giữ tối đa hai thành phần active và không ghi đè WIP.

**Lệnh baseline tối thiểu:** `git status --short`, `git rev-parse HEAD`, đọc workflow/run URL trên SHA; `PYTHONPATH=services/agent-hub ENVIRONMENT=test python3 -m pytest tests/evals services/agent-hub/tests -q` cho Hub; lệnh `make test-retail`, `make test-ops`, `make test-quan`, `python platform/aks-sre-platform/tests/test_gates.py` chỉ khi task liên quan và đọc Makefile/runtime trước. Không báo “all green” nếu một lệnh fail, job skipped hoặc CI trên SHA khác. Lệnh cloud/cluster phải ghi context và không chạy apply/destroy tự động.
