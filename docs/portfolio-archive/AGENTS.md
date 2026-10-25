# Quy tắc cho mọi AI coding session trong Senior Engineering Monorepo

1. **Nguồn trạng thái và kiểm tra trước khi sửa:**
   Đọc `STATUS.md`, `PHASES.md`, `AGENTS.md` của từng service/platform con, plan/task và ADR liên quan. **STATUS.md là snapshot có timestamp; Git/CI live mới là nguồn trạng thái hiện tại.** Kiểm tra Git branch, HEAD/remote main, PR và CI **trước khi sửa**. Khi repo có `.codegraph/`, dùng CodeGraph để tìm hiểu code trước khi rg/đọc file.

2. **Cặp Active giới hạn:**
   Tối đa **hai thành phần active** (services/workloads) được sửa cùng lúc. Cặp hiện hành: `services/retail-finance` + `services/opsbridge-flashsale`. Chỉ chuyển cặp theo Gate được định nghĩa trong `STATUS.md` và `PHASES.md`. Không cho nhiều agent sửa cùng file.

3. **Runtime & Code-Docs Alignment (Bắt buộc chính xác):**
   - `services/retail-finance`: **Java 17** (Maven), Python 3.11 (recon).
   - `services/opsbridge-flashsale`: **.NET 10** (`net10.0`), C# 13.
   - `services/quanlykho`: **Python 3.11** (FastAPI / Poetry / Alembic).
   - `platform/aks-sre-platform`: **Python 3.11** (`.venv`), Terraform, K8s, ArgoCD.
   - Không được ghi sai phiên bản ngôn ngữ/framework trong tài liệu và PR.

4. **Khai báo Task chuẩn Senior:**
   Mỗi task phải nêu: **vấn đề doanh nghiệp → invariant/rủi ro → phạm vi file/owner → cách tái hiện lỗi trước sửa → thay đổi nhỏ nhất → lệnh và output thật → dữ liệu bền vững sau lỗi → claim được phép nói**. Test pass mà thiếu DB/queue/rollback evidence không đóng gate tương ứng.

5. **Gắn kết quả với Exact-SHA:**
   Gắn toàn bộ kết quả với exact SHA, môi trường, dữ liệu (synthetic/real), đầu vào tải, URL CI và artifact raw. CI trên SHA khác, job skipped, green badge, unit test hay tài liệu ghi “PASS” đều không chứng minh delivery/production. Chưa chạy ghi `NOT_VERIFIED`; không sửa test để nới invariant nghiệp vụ.

6. **Ranh giới kiến trúc & dữ liệu (Strict Boundaries):**
   - `services/retail-finance`: MySQL sở hữu ledger; broker/cache không quyết định ghi tiền.
   - `services/opsbridge-flashsale`: PostgreSQL sở hữu stock/order; Redis chỉ fast-fail, queue at-least-once cần idempotency.
   - `services/quanlykho`: PostgreSQL sở hữu tồn và approval; AI chỉ tư vấn trên phiếu canonical.
   - `platform/aks-sre-platform`: Sở hữu Terraform/state/identity/GitOps/policy/observability; workload sở hữu image/migration/overlay/probes/business metrics.
   - Kafka, RabbitMQ, Redis chỉ thêm khi có use case, consumer, failure model và phép đo cụ thể.

7. **Bảo vệ Secret & Quyền Cloud:**
   Không đưa secret/PII vào repo, PR hoặc log. Cloud apply/destroy và sửa ledger/đơn thật phải qua human approval. Cloud action cần known state owner, OIDC/quyền, quota/budget, reviewed saved plan và manual environment gate. Không tự apply khi push.

8. **Kết thúc task:**
   Kết thúc task bằng: file và dòng thay đổi, test command → output thật, CI SHA/URL, evidence artifact, rủi ro còn lại và DONE/PARTIAL/BLOCKED. Nếu task bị chặn, để lại bước tái hiện và đầu vào cụ thể còn thiếu.

Thứ tự triển khai và điều kiện dừng nằm trong [PHASES.md](PHASES.md); trạng thái live và cặp active ở [STATUS.md](STATUS.md).
