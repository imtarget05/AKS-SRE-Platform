# Handoff: đóng các gate thật của bốn repo và Agent Hub

**Snapshot:** 2026-10-24. Đây là plan, không phải chứng nhận hoàn thành. Trước mỗi phase phải đọc lại `AGENTS.md`, `PHASES.md`, `STATUS.md`, Git/CI/AKS live. `STATUS.md` là snapshot có thể đã cũ. Tối đa hai thành phần active; một integrator sửa mỗi file. Không reset/stash/commit WIP của phiên khác.

## Trạng thái đầu vào phải xác nhận lại

| Nguồn | Snapshot đã kiểm tra | Việc cần nhớ |
| --- | --- | --- |
| Monorepo `Senior-Engineering-Portfolio` | `origin/main` `a7229d5`; run `40104051421` xanh 6/6 trên SHA **khác** `074a494`; run trên `a7229d5` chỉ path-filter, năm job skipped. | Không dùng badge xanh của docs-only SHA làm bằng chứng test 4 service. |
| Retail canonical | `origin/main` `ffff464`; `backend-ci` run `40105131860` thất bại trước assertion MySQL: Testcontainers Docker API 1.32, runner yêu cầu tối thiểu 1.40. | CodeQL xanh không bù được integration đỏ. |
| OpsBridge canonical | local branch `codex/ops-retry-edge-20261024`, commit `1821d4a` **ahead origin**; còn WIP rate limiting/Cloudflare trong checkout. | Đã có owner API HMAC cho đúng một `MessageId`, audit/idempotency transaction. Chưa vào `origin/main`. |
| AKS Platform canonical | local branch `codex/platform-edge-gate-20261024`, commits `340023d`, `28aa0e5` **ahead origin**; còn WIP Argo trong checkout. | Đã có Hub pilot an toàn hơn, nhưng chưa có Agent Hub CI/image publish và chưa live end-to-end. |
| QuanLyKho canonical | `main` `1bb494a`; production overlay còn Secret `CHANGE_ME`, namespace/route placeholder. | **Cấm sync production overlay hiện tại.** |
| AKS `aks-portfolio-dev` | Agent Hub `0/1 ImagePullBackOff`, GHCR 403; Argo `flashsale`/`quanlykho` OutOfSync/Missing, chưa có pod hai workload. | CRD Gateway/KEDA tồn tại chỉ là platform prerequisite. |

## Hợp đồng kỹ thuật được phép dùng

- **OpsBridge owner:** `src/Order.Api/Program.cs` bốn `/internal/agent/outbox/*` endpoint; `src/Order.Api/Auth/AgentRecoveryAuth.cs` ký method/path/timestamp/body hash; `src/FlashSale.Infrastructure/Persistence/OutboxRecoveryService.cs` compare-and-update một event với `DeadLetteredAt`, ghi `OutboxRecoveryCommands` cùng transaction; `tests/IntegrationTests/OutboxEndpointTests.cs` là mẫu kiểm thử PostgreSQL thật.
- **Agent Hub canonical:** `AKS-SRE-Platform/apps/agent-hub/core/action_executor.py` allowlist `REPLAY_STUCK_OUTBOX`, reviewer `SRELead`/`SecurityOfficer` khác requester, trạng thái `UNKNOWN` cho kết quả owner chưa biết; `apps/agent-hub/README.md` mô tả hợp đồng và giới hạn. `kubernetes/apps/agent-hub/agent-hub.yaml` hiện chỉ là manifest pilot `agent-hub:local`, một replica/SQLite PVC.
- **Monorepo copy cũ không được dùng làm mẫu thực thi:** `services/agent-hub/core/action_executor.py` còn gọi bulk `POST /api/outbox/requeue`, dùng `after_count <= before_count`; `adapters/ops_adapter.py` tự ký Staff JWT bằng khóa owner. `docs/adr/024-approved-agent-execution.md` còn trạng thái cũ. Không chạy lệnh bulk dưới danh nghĩa intent một event.
- **Retail CI:** `.github/workflows/ci.yml` chạy `mvn -B verify`; `backend/pom.xml` kế thừa Testcontainers 1.19.7 qua Spring Boot 3.2.5. Monorepo `services/retail-finance/backend/pom.xml` có bản vá ứng viên Testcontainers 1.20.4 đã qua CI monorepo; phải kiểm chứng lại trong canonical. Docker docs xác nhận API client 1.32 thấp hơn mức server 1.40; không dùng ép `DOCKER_API_VERSION` làm giải pháp dài hạn vì nó tắt negotiation: <https://docs.docker.com/reference/api/engine/>.
- **AKS image:** có thể tham khảo `AKS-SRE-Platform/.github/workflows/legacyapp-ci.yml` cho OIDC → ACR → image SHA/digest và `.github/workflows/aks-deploy.yml` cho manual environment/saved plan. AKS pull ACR cần đúng quyền của kubelet identity (`AcrPull`, hoặc repository reader với ABAC): <https://learn.microsoft.com/en-us/azure/aks/cluster-container-registry-integration>. Không giả định GHCR 403 sẽ hết nếu chỉ gắn ACR.

## Phase 0 — Khóa baseline, owner và bằng chứng (read-only)

**Làm:** ghi `git status --short --branch`, HEAD, `origin/main`, diff đang dở, CI run/SHA/job conclusion của từng repo; kiểm tra context AKS, pod/Argo/image/Secret key names nhưng không in secret values. Tạo bảng `claim → nguồn → trạng thái VERIFIED/FAILED/NOT_VERIFIED`. Tạo ADR ngắn xác định **canonical repos là nguồn code**, monorepo là bản tích hợp/evidence; chọn một cơ chế đồng bộ (subtree/script có hash hoặc CI drift check), không copy tay không kiểm tra.

**Gate:** tài liệu chỉ ra chính xác ai sở hữu file. Nếu WIP của phiên khác chưa rõ owner, giữ nguyên file đó và nêu blocker; không reset/stash. Không chuyển phase khi base branch/SHA chưa xác định.

## Phase 1 — Retail + OpsBridge: CI và owner command

**Retail owner:** `backend/pom.xml`, `.github/workflows/ci.yml`, test infrastructure. Reproduce CI error bằng log run `40105131860`; xem `mvn dependency:tree` và phiên bản Docker runner. Dùng override Testcontainers tương thích từ monorepo làm **ứng viên**, chọn version theo dependency tree và release docs, không sửa business assertion hoặc skip Failsafe. Chạy `cd backend && mvn -B clean verify`, sau đó PR/CI canonical trên **cùng SHA**: unit và MySQL 8 Testcontainers IT thật đều chạy, không có 33 initialization errors. Unit-green một mình không đạt gate.

**Ops owner:** review commit `1821d4a`, `Program.cs`, `OutboxRecoveryService.cs`, migration, HMAC auth, test. Giữ các WIP rate limiting/Auth/Web/overlay của phiên khác ngoài commit. Bổ sung test giá trị: hai event dead-lettered cùng lúc → duyệt UUID A chỉ A thay đổi; B giữ nguyên; stale version 409; signature/body tamper 401; retry sau mất response trả đúng một audit; hai request đồng thời cùng key không có double effect. `dotnet test tests/IntegrationTests/FlashSale.IntegrationTests.csproj`, `dotnet test tests/UnitTests/FlashSale.UnitTests.csproj`, `bash scripts/validate-manifests.sh`. PR riêng; chỉ merge khi canonical CI trên merge SHA xanh.

**Gate chuyển cặp:** Retail `backend-ci` xanh trên merge SHA và OpsBridge owner command xanh trên merge SHA. Nếu Retail CI vẫn đỏ, giữ cặp này; không chuyển sang cloud.

## Phase 2 — OpsBridge + AKS Platform: hợp nhất HITL, chứng minh end-to-end local

**Platform owner:** tích hợp commits `340023d`, `28aa0e5` vào PR canonical; thêm job Agent Hub Python tests + evals vào Platform CI, build/publish image có digest, kiểm tra manifest render. Đừng dùng Staff JWT signing key của OpsBridge hoặc token tĩnh của Hub để điều khiển outbox. Approval phải khác requester, bind exact `run_id + scope + MessageId + DeadLetteredAt + idempotency_key` và có TTL. Owner API thực thi, Hub không ghi DB nghiệp vụ trực tiếp. Chuyển run `UNKNOWN` khi network mất sau owner commit, retry cùng key nhận receipt gốc.

**Monorepo integrator:** sau khi canonical merge, thay bản Hub/owner copy cũ bằng mã từ canonical có đối chiếu diff/SHA; cập nhật ADR 024/STATUS theo trạng thái thật. Thêm drift gate để phát hiện xuất hiện lại `/api/outbox/requeue` trong Hub executor hoặc `_generate_staff_token` với owner signing key. Không sửa test để hợp thức hóa bulk command.

**Business drill bắt buộc:** trên môi trường cô lập, chạy Agent Hub thật → Order.Api thật → PostgreSQL thật. Seed ít nhất hai dead-lettered event có ID khác nhau; tạo investigation/evidence, intent A, reviewer độc lập, execute. Chụp DB trước/sau: chỉ A requeue, B không đổi, một row `OutboxRecoveryCommands`, receipt gắn đúng A/key/hash. Inject mất response sau commit và worker crash/retry; kiểm tra không có duplicate effect. Chạy thêm self-approval, cross-scope, expired intent, tampered hash, owner 409. Python `MockTransport` + .NET Testcontainers riêng lẻ **chưa** thay thế drill này.

**Gate:** hai PR canonical và monorepo CI trên exact merged SHA xanh; raw test/DB/log artifact cho drill. Claim được phép: “approval-gated single-event recovery verified in isolated environment”; chưa claim AKS/production.

## Phase 3 — AKS Platform + QuanLyKho: đóng đường deploy thật

**Platform owner trước cloud action:** kiểm tra Azure subscription, owner Terraform state, quota/budget, identity/OIDC và registry. Chọn **một** registry/identity path; nếu ACR thì publish image Agent Hub theo digest và cấp pull permission cho AKS kubelet identity, rồi cập nhật manifest bằng digest. Provision secret bằng Key Vault/External Secrets hoặc quy trình out-of-band có rotation; không commit Secret hay khóa ký. Gate CI phải chứng minh image tồn tại, digest đúng và manifest chỉ tham chiếu đúng digest. Kết quả `kubectl apply` tạo Deployment/PVC/Service không phải workload ready.

**Quan owner trước Argo sync:** sửa `infra/k8s/base/kustomization.yaml` để production render không chứa `secret-template.yaml`/`CHANGE_ME`; giữ Secret material ngoài Git. Sửa namespace Argo destination khớp overlay `bankops-prod`, tên Service sau `prod-` prefix, route/host thật; quyết định ingress contract với Envoy Gateway thay vì giữ nginx mặc định không có controller. Migration job, image digest, probes và rollback phải render đúng. `kubectl kustomize infra/k8s/overlays/production` + machine assertion: 0 `CHANGE_ME`, 0 Secret material, namespace/Service/HTTPRoute đúng. Overlay Azure của OpsBridge phải **được commit ở revision Argo trỏ đến**; thư mục untracked hiện tại không đủ.

**Cloud execution:** chỉ sau human review của manifest/digest/secret/chi phí/saved plan và environment approval; không tự `terraform apply`, `kubectl apply` hay Argo sync từ lời nhắc plan này. Sau phê duyệt, đo pod readiness, Argo Synced/Healthy, request qua gateway, migration, metrics/alert, rollback và backup/restore. Ghi thời gian và trạng thái trước/sau; Kind không thay bằng chứng AKS. Nếu image vẫn 403 hoặc workload 0/1 thì gate FAIL.

## Phase 4 — Đóng bằng chứng và hồ sơ phỏng vấn (mỗi lần một repo)

Đối chiếu README/STATUS/CV/case study với **exact SHA, CI URL, job không skipped, môi trường, synthetic data, DB/broker state, image digest, Argo health, fault/restore log và giới hạn còn lại**. Gắn nhãn `NOT_VERIFIED` cho phần chưa chạy. Ba case study: Retail transaction/permission; Ops one-event recovery; Platform golden path qua Ops + Quan. Không dùng “production ready”, “zero downtime”, “RTO/RPO” nếu chưa đo đúng workload trong đúng môi trường.

## Format bắt buộc cho AI sau mỗi phase

`DONE/PARTIAL/BLOCKED`; repo/branch/base/commit; file owner và diff; RED reproduction → GREEN command/output; CI URL+exact SHA+job conclusions; dữ liệu trước/sau; môi trường; quyền/phê duyệt; rủi ro còn lại; claim được phép nói. Phase không đạt gate thì giữ nguyên cặp active và để lại bước tái hiện cụ thể.