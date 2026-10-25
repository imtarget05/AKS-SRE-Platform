# Sơ đồ luồng hệ thống — bản chính

Bốn hình này thay thế sơ đồ khối trước đó. Chúng tách **luồng nghiệp vụ**, **Cloudflare/Azure hiện trạng**, **kiến trúc hybrid đích** và **Agent execution theo ADR 024**.

1. [Luồng end-to-end bốn repo](01-end-to-end-runtime-flow.png): nguồn yêu cầu → API/xác thực → xử lý đồng bộ và bất đồng bộ → database sở hữu dữ liệu → kết quả. FlashSale và OpsBridge được vẽ thành hai bounded context với hai database riêng. Dải dưới là platform, SRE và điểm kết nối Agent Hub.
2. [Agent thực thi sau Human in the Loop](02-agent-approved-execution.png): Agent đọc chứng cứ, tạo `ActionIntent`, policy đánh giá, người có quyền duyệt đúng intent, Agent executor gọi command API/Argo, rồi đọc lại trạng thái bền vững để xác minh.
3. [Cloudflare + Azure hiện trạng](03-cloudflare-azure-as-is.png): Cloudflare Workers Assets đang trả Web, Worker API proxy có upstream configured nhưng business probe timeout; Modal URL ghi trong tài liệu báo workspace disabled. AKS control plane/Argo đang chạy nhưng FlashSale và QuanLyKho `OutOfSync/Missing`, chưa có business pod hoặc Gateway API resource.
4. [Cloudflare Edge → Azure AKS đích](04-cloudflare-azure-target.png): đường traffic qua Access/WAF, cloudflared Tunnel, Envoy Gateway đến owner APIs; đường release GitHub/OIDC/ACR/Argo; Agent thực thi sau phê duyệt. Tất cả liên kết chưa được kiểm chứng trên AKS được vẽ nét đứt.

SVG cùng tên là bản vector có thể phóng to. Chạy `python3 docs/architecture/four-repo-runtime/generate.py` cho hình 1–2 và `python3 docs/architecture/four-repo-runtime/generate_cloud.py` cho hình 3–4. Thiết kế chi tiết và release gate nằm ở [ADR 024](../../adr/024-approved-agent-execution.md).

## Trạng thái phải nói đúng

- Runtime domain và đường Kind được vẽ từ [`STATUS.md`](../../../STATUS.md), ADR Retail/Ops/Quan và evidence trong repo. Các phép đo 50/10 và DR là synthetic, gắn môi trường và SHA trước khi dùng trong CV.
- **Agent execution chưa được triển khai.** Agent Hub hiện có read adapters, verifier, proposal và ghi nhận human decision; `ACCEPT_HYPOTHESIS` chưa phải approval để thi hành một action. Hình thứ hai là kiến trúc cần implement và kiểm chứng theo từng command family.
- Agent có quyền gọi lệnh **sau khi** human approval hợp lệ, bằng identity ngắn hạn và endpoint allowlist. Dịch vụ sở hữu dữ liệu/Argo vẫn kiểm quyền, version, idempotency và audit lần nữa. Không có quyền SQL hoặc shell tùy ý.
- Cloud AKS application delivery vẫn là gate riêng. Cụm Kind xanh không chứng minh production readiness trên Azure.
- Cloudflare hiện có **Workers Assets** phục vụ Flutter Web, một API Worker có khả năng reverse proxy khi `UPSTREAM_API_URL` được cấu hình, và cấu hình **Pages** cho OpsBridge Web. `infra/k8s/base/cloudflare-tunnel.yaml`, Workers AI và R2 có source/config nhưng không có bằng chứng tương ứng đã chạy trong AKS hiện tại. Đường Cloudflare → AKS là **target**, không phải current.

## Read-only snapshot ngày 2026-10-24, khoảng 18:44 ICT

- `curl` đến Flutter Workers Assets và `version.json`: HTTP 200, build `eb446f8`. API Worker `/` trả `status: proxy`, nhưng `/api/v1/health/live` là health của Worker; hai GET business/docs qua proxy timeout ở 12 giây. URL Modal ghi trong tài liệu trả `workspace ... is disabled`; giá trị secret `UPSTREAM_API_URL` hiện tại không đọc được nên không khẳng định Worker đang trỏ đúng URL Modal đó.
- `az aks list`: `aks-portfolio-dev` có `Succeeded`. `kubectl --context aks-portfolio-dev get applications -n argocd`: FlashSale và QuanLyKho đều `OutOfSync/Missing`. Hai namespace chưa có business pod; cluster chưa có Gateway API resource; không tìm thấy deployment `cloudflared`.
- Các trạng thái trên có thể thay đổi sau snapshot. Chạy lại read-only probes và gắn exact SHA trước khi dùng làm claim phỏng vấn.

Nguồn kiểm tra: [`Quan deploy workflow`](../../../services/quanlykho/.github/workflows/deploy-pages.yml), [`Worker proxy`](../../../services/quanlykho/infra/cloudflare-worker/src/index.ts), [`Tunnel manifest`](../../../services/quanlykho/infra/k8s/base/cloudflare-tunnel.yaml), [`Quan Argo Application`](../../../platform/aks-sre-platform/platform/argocd/applications/quanlykho.yaml), [`OpsBridge Pages config`](../../../services/opsbridge-flashsale/src/OpsBridge.Web/wrangler.toml), [`Azure evidence`](../../../platform/aks-sre-platform/docs/evidence/azure-aks-cloud-deployment-PASS.md).

## Pilot thực thi đề nghị

OpsBridge `replay one DLQ event` là pilot đầu tiên vì owner API đã có role gate, state transition và audit. Chỉ khi approval hash, scope/version, duplicate/lost-response, audit và post-state proof xanh mới mở thêm lệnh cho QuanLyKho, platform; lệnh ghi tiền Retail đặt sau dual-control ledger gate.
