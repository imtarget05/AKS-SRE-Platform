# Bản đồ kiến trúc bốn repo — 2026-10-24

> **Đã được thay thế về luồng runtime và Agent authority.** Xem [sơ đồ luồng hệ thống bản chính](../four-repo-runtime/README.md) và [ADR 024](../../adr/024-approved-agent-execution.md). Hình 01/04 dưới đây phản ánh thiết kế Agent chỉ đọc trước khi yêu cầu thực thi kèm Human in the Loop được chốt; không dùng chúng để mô tả kiến trúc đích.

Đây là **bốn hình 16:9** để trình bày kiến trúc khi phỏng vấn. Mỗi hình có bản PNG để xem nhanh và SVG để phóng to hoặc sửa. `generate.py` là nguồn tạo các SVG; chạy lại script rồi dùng `sips -s format png <file>.svg --out <file>.png` để xuất PNG trên macOS.

| Hình | Câu hỏi kiến trúc cần trả lời |
| --- | --- |
| [01 · System landscape](01-system-landscape.png) | Context nào sở hữu ledger, order/stock, inventory voucher; platform và Agent Hub có quyền gì? |
| [02 · Transaction & failure flows](02-transaction-and-failure-flows.png) | Retry, concurrency, broker lỗi và maker–checker được chặn ở đâu, kiểm trạng thái bền vững thế nào? |
| [03 · Platform & SRE](03-platform-and-sre.png) | Một release đi từ SHA qua CI/GitOps tới runtime ra sao; rollback, alert, restore và Azure còn thiếu bằng chứng nào? |
| [04 · Agent Hub governance](04-agent-hub-governance.png) | AI đọc dữ liệu qua ranh giới nào, kiểm nguồn ra sao và tại sao không được tự thay đổi ledger/kho/hạ tầng? |

## Cách đọc trạng thái

- **Có triển khai / bằng chứng local hoặc Kind:** các ranh giới domain và các luồng chính theo ADR, CI và tài liệu evidence bên dưới. Nhãn Kind chỉ nói về cluster local, không nói về AKS production.
- **Gate còn mở:** image digest và exact release ref/rollback trên đường phát hành cloud, fault matrix đầy đủ, SLO alert fire/resolve, AKS app sync/rollback/restore/cost. Hình 03 dùng viền hoặc mũi tên đứt tại release contract để tránh nhầm với trạng thái đã kiểm chứng.
- **WIP:** Agent Hub và read adapters cho bốn nguồn là hợp đồng kiến trúc; chưa có chứng cứ end-to-end cho toàn bộ nguồn trong production. Hình 04 dùng đường đứt cho kết nối này.
- Các phép đo DR là **synthetic trên Kind/local**. RTO 0,787 giây và mất 5 đơn delta trong cửa sổ 4 giây là số đo của một drill snapshot, không phải RTO/RPO production hoặc mục tiêu SLA.

## Căn cứ đối chiếu

| Quyết định / claim | Nguồn trong repo |
| --- | --- |
| Ledger MySQL, Kafka/RabbitMQ/Redis chưa ở core path | [`Retail ADR 0001`](../../../services/retail-finance/docs/adr/0001-messaging-boundaries.md), [`Retail ADR 0002`](../../../services/retail-finance/docs/adr/0002-outlet-owned-accounts.md) |
| FlashSale Redis fast-fail, RabbitMQ at-least-once, PostgreSQL truth | [`Ops README`](../../../services/opsbridge-flashsale/README.md), [`Ops ADR 019`](../../../services/opsbridge-flashsale/docs/adr/019-transactional-outbox.md) |
| OpsBridge có database và write ownership riêng | [`Ops ADR 017`](../../../services/opsbridge-flashsale/docs/adr/017-opsbridge-bounded-context-foundation.md) |
| FastAPI canonical, branch scope, AI chỉ tư vấn | [`Quan ADR 0001`](../../../services/quanlykho/docs/adr/0001-canonical-api-fastapi-worker-proxy-deprecation.md), [`Quan ADR 0002`](../../../services/quanlykho/docs/adr/0002-ai-governance-and-advisory-boundaries.md), [`Quan ADR 0005`](../../../services/quanlykho/docs/adr/0005-branch-scoping-decision.md) |
| Agent Hub read-only và abstain khi thiếu chứng cứ | [`ADR 023`](../../adr/023-agent-hub-boundary-and-read-only-invariants.md), [`Hub evidence`](../../evidence/multi-agent-system-e2e-evidence.md) |
| Kind, Argo/Envoy, DR local và trạng thái gate | [`STATUS`](../../../STATUS.md), [`Kind release/rollback evidence`](../../evidence/kind-golden-path-rollback-evidence.md), [`DR drill`](../../../platform/aks-sre-platform/docs/evidence/enterprise-dr-drill-with-delta-PASS.md) |

Các tài liệu evidence là snapshot tại thời điểm ghi. Khi dùng hình để phỏng vấn, kiểm tra lại exact SHA, GitHub Actions run, GitOps revision và môi trường trước khi nhắc tới một claim hiện hành. Bốn hình giải thích **thiết kế, luồng và giới hạn đã biết**; chúng không thay thế runbook, threat model, capacity test hoặc audit production.
