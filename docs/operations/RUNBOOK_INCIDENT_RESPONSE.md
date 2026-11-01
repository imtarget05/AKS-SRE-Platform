# Incident Response Runbook — Quy trình 6 bước (Google SRE)

Áp dụng cho: **AKS-SRE-Platform** và **QuanLyKho**

## 0. Quy tắc vàng

> Khi hệ thống đang gián đoạn nghiêm trọng, ưu tiên **khôi phục dịch vụ** trước. Phân tích nguyên nhân gốc (root cause) có thể thực hiện sau khi dịch vụ đã ổn định.

---

## 1. Detect — Phát hiện bất thường

| Nguồn | Cách phát hiện | Công cụ |
|-------|---------------|---------|
| Alerting | SLO burn-rate, error rate > ngưỡng, CPU > 80% | Prometheus + Alertmanager, Grafana |
| Golden Signals | Latency p95 tăng, Traffic突增, Errors 5xx, Saturation CPU/RAM | Grafana dashboard |
| User report | Người dùng báo "ứng dụng không hoạt động" | Support ticket, Slack, email |
| Synthetic probe | Health check `/health/live` thất bại | k6, curl, uptime robot |

**Lệnh kiểm tra nhanh:**

```bash
# AKS
kubectl get nodes
kubectl get pods --all-namespaces | grep -v Running
kubectl get events --all-namespaces --sort-by=.lastTimestamp | tail -20

# QuanLyKho (local)
curl -f http://localhost:8000/api/v1/health/live
```

---

## 2. Assess — Xác định phạm vi ảnh hưởng

| Câu hỏi | Cách trả lời |
|---------|-------------|
| Có bao nhiêu user bị ảnh hưởng? | Xem Grafana traffic dashboard, Access logs |
| Dịch vụ nào bị ảnh hưởng? | Xem Argo CD sync status, pod status |
| Thời điểm bắt đầu? | Xem alert timestamp, event logs |
| Có liên quan đến deploy mới không? | Xem git log, Argo CD revision, image tag |

**Lệnh kiểm tra:**

```bash
# Xem revision hiện tại
kubectl get application <app-name> -o jsonpath='{.status.sync.revision}'

# Xem pod restart count
kubectl get pods -l app=<app-name> -o wide
```

---

## 3. Investigate — Thu thập bằng chứng, khoanh vùng lỗ

### 3.1 Pod Running nhưng API 503 (Kubernetes)

| Bước | Lệnh | Dấu hiệu bất thường |
|------|------|---------------------|
| 1 | `kubectl -n NS get deployments,pods,services` | READY=False, RESTARTS > 0 |
| 2 | `kubectl -n NS describe pod POD` | Readiness probe failed, CrashLoopBackOff, OOMKilled |
| 3 | `kubectl -n NS logs POD --since=15m --tail=200` | Exception stack trace, DB connection timeout |
| 4 | `kubectl -n NS logs POD --previous` | Crash loop trước khi restart |
| 5 | `kubectl -n NS describe service APP` | EndpointSlice rỗng |
| 6 | `kubectl -n NS get endpointslices -l kubernetes.io/service-name=APP` | Không có endpoint sẵn sàng |

### 3.2 API trả HTTP 500 (FastAPI)

| Bước | Lệnh | Dấu hiệu |
|------|------|----------|
| 1 | Application logs + `X-Request-ID` | Exception stack trace |
| 2 | Kiểm tra envelope error | `error.code`, `error.message`, `error.request_id` |
| 3 | Kiểm tra dependency | PostgreSQL, Redis, Cloudflare Edge |
| 4 | Kiểm tra DB connection | `pg_stat_activity` |

### 3.3 API phản hồi chậm (PostgreSQL)

```sql
SELECT
    pid,
    state,
    wait_event_type,
    wait_event,
    now() - xact_start AS transaction_age,
    now() - query_start AS query_age
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY xact_start NULLS LAST;
```

| Quan sát | Hướng suy luận |
|----------|---------------|
| `wait_event_type = Lock` | Chờ transaction khác nhả khóa |
| `idle in transaction` kéo dài | Giao dịch chưa kết thúc, giữ tài nguyên/khóa |
| Nhiều phiên xử lý kéo dài | Truy vấn chậm, quá tải, dependency |
| Nhiều kết nối gần giới hạn | Connection pool rò rỉ, cần tăng max_connections |

### 3.4 Hai người duyệt phiếu kho đồng thời (QuanLyKho)

| Kiểm tra | Cách xác minh |
|----------|--------------|
| Transaction isolation | `SELECT ... FOR UPDATE` khóa hàng |
| Idempotency key | Cùng key chỉ xử lý 1 lần |
| 409 Conflict | Kết quả đúng của cơ chế bảo vệ nghiệp vụ |
| Movement trùng | Không được có duplicate movement trong DB |

---

## 4. Mitigate — Giảm ảnh hưởng, khôi phục dịch vụ

| Tình huống | Hành động giảm ảnh hưởng | Lệnh |
|-----------|------------------------|------|
| Deploy mới gây lỗi | Rollback về bản ổn định | `kubectl rollout undo deployment APP` |
| Pod crash loop | Scale về 0, sau scale lại | `kubectl scale deployment APP --replicas=0` |
| DB bị chậm | Kill transaction dài hạn | `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE ...` |
| Traffic突增 | Rate limiting, scale up | HPA, KEDA, Cloudflare rate limit |

**Quyết định rollback:** Nếu lỗi xuất hiện sau deploy mới và chưa khắc phục được trong 5 phút → revert Argo CD Application về revision trước.

---

## 5. Verify — Kiểm chứng hệ thống đã phục hồi

| Kiểm tra | Lệnh | Kết quả mong đợi |
|----------|------|------------------|
| Health check | `curl -f /api/v1/health/live` | HTTP 200 |
| Pod ready | `kubectl get pods` | READY=1/1, STATUS=Running |
| Argo CD sync | `kubectl get application APP` | Synced, Healthy |
| Error rate | Grafana dashboard | 5xx < 0.1% |
| Latency p95 | Grafana dashboard | < 200ms |

---

## 6. Postmortem — Phân tích nguyên nhân và phòng ngừa

Sử dụng template `INCIDENT_REPORT_TEMPLATE.md`.

| Phần | Nội dung |
|------|----------|
| Timeline | Thời điểm phát hiện, bắt đầu xử lý, khôi phục |
| Tác động | Số user affected, thời gian downtime, loss estimation |
| Nguyên nhân gốc | Root cause (5 Whys) |
| Bằng chứng | Logs, metrics, traces, screenshots |
| Xử lý đã thực hiện | Mitigate actions, rollback |
| Phòng ngừa | Action items, owner, deadline |

---

## Escalation Matrix

| Mức độ | Ngân hàng | Thời gian phản hồi | Người liên hệ |
|--------|-----------|-------------------|---------------|
| P1 — Production down | SRE Lead | < 15 phút | SRE Lead, Platform Architect |
| P2 — Degraded performance | On-call SRE | < 30 phút | On-call SRE |
| P3 — Minor bug | Dev team | < 4 giờ | Backend Maintainer |

---

## Runbook liên quan

- `RUNBOOK_POD_RUNNING_503.md` — Debug Pod Running nhưng API 503
- `RUNBOOK_API_500_FASTAPI.md` — Debug API trả 500
- `RUNBOOK_API_SLOW_POSTGRESQL.md` — Debug API chậm do PostgreSQL
- `RUNBOOK_QH_409_CONFLICT.md` — Hai người duyệt phiếu kho đồng thời
- `INCIDENT_REPORT_TEMPLATE.md` — Template báo cáo sự cố