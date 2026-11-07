# Runbook: Deploy Render + ArgoCD sau khi sửa DB (12 bước)

> Toàn bộ secret đi qua `scripts/.env` (gitignored), không dán vào chat, không commit.
> Bất kỳ token nào đã từng xuất hiện ở chat/log/file → coi như bị lộ → **rotate trước** khi deploy.

## Giả định trước khi chạy
- Bạn đang dùng máy có quyền thật: dashboard Render, `argocd` CLI + quyền trên cluster.
- Đã `cp scripts/.env.example scripts/.env` và điền giá trị **mới sau rotation**.

## 12 bước

| # | Bước | Lệnh / nơi làm |
|---|------|----------------|
| 1 | Rotate toàn bộ token đã lộ (GitHub PAT, Neon, Cloudflare, Render API key + key trong deploy-hook URL, SonarQube) | Revoke token cũ → tạo token mới, scope tối thiểu |
| 2 | Tạo env file từ template | `cp scripts/.env.example scripts/.env` → điền giá trị MỚI |
| 3 | Render: đặt `SPRING_DATASOURCE_URL/USERNAME/PASSWORD` (hoặc biến DB tương ứng backend) | Render dashboard → Service → Environment → Save |
| 4 | Trigger preview redeploy | `source scripts/.env && ./scripts/deploy-render.sh` |
| 5 | Xem logs preview: KHÔNG được có `UnknownHostException`, không lỗi connect DB, app start OK | Render dashboard → Logs |
| 6 | Nếu preview pass → deploy production (dashboard redeploy hoặc deploy-hook cấu hình riêng cho prod) | Render dashboard |
| 7 | Verify production: health endpoint trả HTTP 200, không CrashLoopBackOff | `curl -fsS https://<render-app-url>/health` |
| 8 | Sync ArgoCD app về `main` | `./scripts/sync-argocd.sh` |
| 9 | Chờ về Healthy (timeout 600s trong script) | script tự làm (`argocd app wait`) |
| 10 | Kiểm tra app không degraded, không resource unhealthy | `./scripts/check-argocd.sh` (exit 0 = sạch) |
| 11 | Nếu cần deploy Pages: chỉ cho project DIRECT-UPLOAD; project Git-connected thì push commit để CI deploy | `./scripts/deploy-cloudflare-pages.sh` |
| 12 | Quét máy + repo còn token cũ, thay bằng placeholder | `rg -n 'ghp_|napi_|cfk_|rnd_' --glob '!scripts/.env'` + tìm chuỗi key cũ từng cấp (dán key cũ vào lệnh tìm tại chỗ, không ghi vào file) |

## Checklist kết thúc (phải pass hết trước khi báo hoàn thành)
- [ ] Preview + production deploy trả HTTP 2xx
- [ ] Logs không có exception kết nối DB
- [ ] `./scripts/check-argocd.sh` exit 0
- [ ] Health endpoint trả 200
- [ ] Toàn bộ token cũ đã revoke; token mới chỉ tồn tại trong `scripts/.env`
