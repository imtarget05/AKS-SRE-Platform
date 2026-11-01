# Runbook: Pod Running nhưng API trả 503 Service Unavailable

Áp dụng cho: **AKS-SRE-Platform** (Kubernetes)

## Triệu chứng

- `kubectl get pods` hiển thị `STATUS: Running`
- Nhưng người dùng nhận HTTP `503 Service Unavailable`
- Argo CD hiển thị `Synced`, `Healthy`

## Quy trình điều tra

### Bước 1 — Xem trạng thái tổng thể

```bash
NS=<namespace>
APP=<app-name>

kubectl -n "$NS" get deployments,pods,services
kubectl -n "$NS" rollout status deployment/"$APP"
kubectl -n "$NS" get events --sort-by=.lastTimestamp | tail -30
kubectl -n "$NS" get pods -o wide
```

**Quan sát ba cột:** STATUS, READY, RESTARTS

| Trường | Ý nghĩa |
|--------|---------|
| STATUS | Container/Pod đang ở trạng thái nào |
| READY | Pod có đủ điều kiện phục vụ traffic không |
| RESTARTS | Container đã khởi động lại bao nhiêu lần |

> `Running` chỉ cho biết Pod đã được gán Node và container đang chạy. **Không bảo đảm** ứng dụng đã sẵn sàng phục vụ yêu cầu.

### Bước 2 — Xem lý do Pod không sẵn sàng

```bash
POD=<pod-name>

kubectl -n "$NS" describe pod "$POD"
kubectl -n "$NS" logs "$POD" --since=15m --tail=200
kubectl -n "$NS" logs "$POD" --previous
```

| Dấu hiệu | Khả năng cần kiểm tra |
|----------|---------------------|
| `Readiness probe failed` | Endpoint health check, DB, cổng hoặc ứng dụng chưa sẵn sàng |
| `CrashLoopBackOff` | Ứng dụng crash lặp lại, cấu hình lỗi |
| `OOMKilled` | Container vượt giới hạn bộ nhớ |
| `ImagePullBackOff` | Sai image/tag, thiếu quyền registry, lỗi mạng |
| `FailedScheduling` | Thiếu tài nguyên, constraint, cấu hình scheduling |

### Bước 3 — Kiểm tra ba loại health probe

| Probe | Chức năng | Khi thất bại |
|-------|-----------|-------------|
| Startup | Ứng dụng đã khởi động xong chưa? | Có thể restart nếu vượt ngưỡng |
| Readiness | Ứng dụng có thể nhận traffic chưa? | Ngừng đưa Pod vào endpoint sẵn sàng |
| Liveness | Ứng dụng còn hoạt động không? | Restart container nếu vượt ngưỡng |

### Bước 4 — Kiểm tra Service và EndpointSlice

```bash
kubectl -n "$NS" describe service "$APP"
kubectl -n "$NS" get endpointslices -l kubernetes.io/service-name="$APP"
kubectl -n "$NS" get service "$APP" -o yaml
```

Nếu Service không có endpoint sẵn sàng → kiểm tra labels/selector và readiness.
Nếu có endpoint → kiểm tra `targetPort`, cổng ứng dụng thực sự lắng nghe, kết nối trong cụm, Gateway/Ingress.

### Bước 5 — Ra quyết định xử lý

**Ví dụ kết quả điều tra:**

```
Pod: inventory-api-example
Status: Running
Ready: False
Restart Count: 0

Warning Unhealthy:
Readiness probe failed:
GET /ready -> HTTP 503

Application log:
database connection timeout
```

**Nhận định:** Pod chạy nhưng chưa sẵn sàng vì endpoint `/ready` trả lỗi. Log gợi ý lỗi kết nối database.

**Hướng xử lý:**
1. Kiểm tra DB, Secret/config, DNS, khả năng kết nối
2. Nếu lỗi do bản triển khai mới và chưa khắc phục nhanh được → **rollback**
3. Argo CD với auto-sync: sửa cấu hình mong muốn trong Git, rồi kiểm tra trạng thái đồng bộ

```bash
kubectl -n "$NS" rollout undo deployment "$APP"
```

---

## Kiểm chứng phục hồi

```bash
curl -f http://<service-ip>/api/v1/health/live
kubectl -n "$NS" get pods -l app="$APP"
kubectl -n "$NS" get application "$APP" -o jsonpath='{.status.sync.status}{"\t"}{.status.health.status}'
```

Kết quả mong đợi: HTTP 200, READY=1/1, Synced/Healthy.