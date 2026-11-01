# Runbook: API trả HTTP 500 (FastAPI)

Áp dụng cho: **QuanLyKho** (FastAPI), có thể áp dụng cho AKS-SRE-Platform demo API

## Triệu chứng

- Người dùng nhận HTTP `500 Internal Server Error`
- Application logs có exception stack trace
- Error envelope có `error.code = INTERNAL_ERROR`

## Quy trình điều tra

### Bước 1 — Thu thập bằng chứng từ logs

```bash
# Xem application logs với X-Request-ID
kubectl -n <NS> logs -l app=<app-name> --since=30m --tail=200 | grep -i "error\|exception\|traceback"

# Hoặc local development
tail -f /path/to/app.logs | grep -i "unhandled"
```

**Dấu hiệu bất thường:**
- Exception stack trace (SQLAlchemy, psycopg2, redis, etc.)
- `request_id` trong log có thể liên kết với request cụ thể

### Bước 2 — Kiểm tra error envelope

Response dạng:
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Máy chủ đang gặp sự cố. Vui lòng thử lại sau ít phút.",
    "request_id": "abc123def456",
    "details": {}
  }
}
```

| Trường | Ý nghĩa |
|--------|---------|
| `error.code` | Mã lỗi chuẩn (docs/06:44) |
| `error.message` | Thông điệp an toàn cho người dùng |
| `error.request_id` | Trace liên kết với logs |
| `error.details` | Chi tiết bổ sung (nếu có) |

### Bước 3 — Phân loại lỗi

| Loại lỗi | Dấu hiệu | Hướng xử lý |
|----------|----------|-------------|
| Lỗi kỹ thuật (exception) | Stack trace, 500 | Xem logs, sửa code, rollback |
| Lỗi kết nối DB | `connection timeout`, `connection refused` | Kiểm tra PostgreSQL, Secret/config |
| Lỗi dependency ngoài | Redis, Cloudflare, API bên thứ 3 | Kiểm tra dịch vụ phụ thuộc |
| Lỗi business logic | `AppError` với code cụ thể | Xem `RUNBOOK_QH_409_CONFLICT.md` |

### Bước 4 — Kiểm tra PostgreSQL (nếu liên quan DB)

```sql
SELECT
    pid,
    state,
    wait_event_type,
    wait_event,
    now() - xact_start AS transaction_age
FROM pg_stat_activity
WHERE datname = current_database()
  AND state != 'idle'
ORDER BY xact_start NULLS LAST;
```

Nếu có transactionIdle dài hạn → có thể gây khóa và dẫn đến 500.

### Bước 5 — Hướng xử lý

| Tình huống | Hành động |
|-----------|-----------|
| Lỗi code sau deploy mới | Rollback: `kubectl rollout undo deployment APP` |
| Lỗi cấu hình/Secret | Cập nhật ConfigMap/Secret, restart pod |
| Lỗi DB connection | Kiểm tra PostgreSQL status, connection pool |
| Lỗi chưa xác định | Tăng log level, thu thập thêm bằng chứng |

---

## Kiểm chứng phục hồi

```bash
curl -f http://<api-endpoint>/api/v1/health/live
# Mong đợi: HTTP 200

# Kiểm tra error rate trên Grafana
# Mong đợi: 5xx < 0.1%
```