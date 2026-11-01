# Runbook: API phản hồi chậm do PostgreSQL

Áp dụng cho: **QuanLyKho** (FastAPI + PostgreSQL), **AKS-SRE-Platform** (demo API)

## Triệu chứng

- Trước đây yêu cầu lấy danh sách tồn kho mất 150 ms, bây giờ mất 3 giây+
- p95 latency tăng rõ rệt trên Grafana
- CPU ứng dụng có thể thấp (không phải do ứng dụng)

## Quy trình điều tra

### Bước 1 — Kiểm tra Golden Signals

| Chỉ số | Cách kiểm tra | Ngưỡng bất thường |
|--------|--------------|-------------------|
| Latency p95/p99 | Grafana dashboard | p95 > 2.000 ms |
| Traffic (RPS) | Grafana dashboard | Tăng đột ngột |
| Errors (5xx) | Grafana dashboard | Tăng lên > 1% |
| Saturation (CPU/RAM) | Node metrics | CPU > 80%, RAM > 85% |

### Bước 2 — Kiểm tra PostgreSQL活动

```sql
SELECT
    pid,
    state,
    wait_event_type,
    wait_event,
    now() - xact_start AS transaction_age,
    now() - query_start AS query_age,
    query
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY xact_start NULLS LAST;
```

| Quan sát | Hướng suy luận |
|----------|---------------|
| `wait_event_type = Lock` | Chờ transaction khác nhả khóa |
| `idle in transaction` kéo dài | Giao dịch chưa kết thúc, giữ tài nguyên/khóa |
| Nhiều phiên xử lý kéo dài | Truy vấn chậm, quá tải, dependency |
| Nhiều kết nối gần giới hạn | Connection pool rò rỉ |

### Bước 3 — Phân tích truy vấn chậm

```sql
-- Chỉ chạy EXPLAIN trên truy vấn SELECT an toàn (không chạy ANALYZE trên ghi dữ liệu ở production)
EXPLAIN (BUFFERS) SELECT ...;
```

Nếu thấy `Seq Scan` trên bảng lớn → cần thêm index hoặc rewrite query.

### Bước 4 — Kiểm tra connection pool

```sql
SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();
```

So sánh với `max_connections` của PostgreSQL. Nếu gần giới hạn → kiểm tra connection pool configuration (SQLAlchemy pool_size, max_overflow).

---

## Hướng xử lý

| Tình huống | Hành động |
|-----------|-----------|
| TransactionIdle dài hạn | Kill transaction: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction'` |
| Truy vấn chậm | Thêm index, rewrite query, chạy EXPLAIN ANALYZE ở staging |
| Connection pool đầy | Tăng pool_size, kiểm tra rò rỉ kết nối (không close connection) |
| PostgreSQL quá tải | Scale up DB, đệm cache (Redis) |

---

## Kiểm chứng phục hồi

```bash
# Kiểm tra latency p95 trên Grafana
# Mong đợi: p95 < 200ms (hoặc về mức baseline)

# Kiểm tra pg_stat_activity không còn transactionIdle dài hạn
# Kiểm tra connection count < 80% max_connections
```