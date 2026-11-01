# Runbook: Hai người duyệt phiếu kho đồng thời (409 Conflict)

Áp dụng cho: **QuanLyKho** (FastAPI + PostgreSQL)

## Triệu chứng

- Hai người checker cùng duyệt một phiếu kho (#101) gần như đồng thời
- Request A: thành công (200 OK), ghi movement một lần
- Request B: nhận `409 Conflict`, trạng thái phiếu đã được duyệt
- **409 Conflict có thể là kết quả đúng** của cơ chế bảo vệ nghiệp vụ, không phải sự cố máy chủ

## Cơ chế bảo vệ (theo tài liệu dự án)

| Cơ chế | Mục đích | Cách triển khai |
|--------|----------|-----------------|
| `SELECT ... FOR UPDATE` | Khóa hàng khi kiểm tra tồn kho | Trong transaction, trước khi giảm tồn kho |
| Kiểm tra trạng thái phiếu | Chỉ cho phép duyệt nếu phiếu ở trạng thái pending | `WHERE status = 'pending'` |
| Idempotency key | Tránh xử lý lại cùng thao tác hai lần | Header `Idempotency-Key` |
| Optimistic lock (version) | Phát hiện ghi đè dữ liệu | `StaleDataError` → 409 `VERSION_CONFLICT` |

## Quy trình điều tra

### Bước 1 — Kiểm tra API response

| Request | Status Code | Body | Ý nghĩa |
|---------|-------------|------|---------|
| Checker A | 200 OK | `{"status": "approved", ...}` | Thành công |
| Checker B | 409 Conflict | `{"error": {"code": "IDEMPOTENCY_KEY_REUSED" or "VERSION_CONFLICT", ...}}` | Phiếu đã được duyệt |

### Bước 2 — Kiểm tra logs

```bash
# Tìm logs với request_id của request B
kubectl -n <NS> logs -l app=<app-name> | grep "request_id=<checker-b-request-id>"
```

Tìm dấu hiệu:
- `IDEMPOTENCY_KEY_REUSED`: cùng idempotency key đã được dùng
- `VERSION_CONFLICT`: optimistic lock bị ghi đè
- `CONSTRAINT_VIOLATION`: vi phạm unique constraint

### Bước 3 — Kiểm tra database

```sql
-- Kiểm tra trạng thái phiếu
SELECT id, status, version, updated_at FROM inventory_orders WHERE id = 101;

-- Kiểm tra movement (không được duplicate)
SELECT * FROM inventory_movements WHERE order_id = 101 ORDER BY created_at;
```

| Kiểm tra | Kết quả mong đợi |
|----------|-----------------|
| `status` | `approved` (không được thay đổi sau lần đầu) |
| `version` | Tăng lên 1 (chỉ 1 lần) |
| `inventory_movements` | Chỉ có 1 dòng cho order_id = 101 |

### Bước 4 — Hướng xử lý

| Tình huống | Hành động |
|-----------|-----------|
| 409 Conflict do idempotency key trùng | Không xử lý lại, trả 409 cho client, client hiển thị "phiếu đã được duyệt" |
| 409 Conflict do version conflict | Client tải lại dữ liệu mới nhất, thử lại nếu cần |
| Duplicate movement (lỗi hệ thống) | Xóa movement trùng, khôi phục tồn kho, điều tra root cause |

---

## Kiểm chứng phục hồi

```bash
# Test hai request cùng idempotency key
curl -X POST /api/v1/approvals/101/approve -H "Idempotency-Key: abc-123" -H "Authorization: Bearer <token-A>"
curl -X POST /api/v1/approvals/101/approve -H "Idempotency-Key: abc-123" -H "Authorization: Bearer <token-B>"

# Mong đợi: Lần 1 = 200 OK, Lần 2 = 409 Conflict
# Database: chỉ có 1 movement cho order_id = 101
```

---

## Phòng ngừa

1. Luôn dùng transaction với `SELECT ... FOR UPDATE` khi kiểm tra tồn kho
2. Luôn kiểm tra trạng thái trước khi ghi (`WHERE status = 'pending'`)
3. Luôn yêu cầu `Idempotency-Key` cho các thao tác ghi (tạo đơn, duyệt, điều kho)
4. Ghi log rõ ràng `request_id` và `correlation_id` để trace