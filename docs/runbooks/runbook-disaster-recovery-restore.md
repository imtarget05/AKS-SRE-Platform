# Runbook: Automated Disaster Recovery & Point-in-Time Database Restore

## 1. Metadata & Classification
- **Trigger:** Cảnh báo P1 về sự cố hỏng hóc dữ liệu nghiêm trọng (catastrophic database corruption, accidental table DROP/TRUNCATE, ransomware lock, hoặc unrecoverable zone outage).
- **Severity:** P0 (Critical Service Outage / Data Loss Emergency)
- **Impact:** Toàn bộ luồng giao dịch bị gián đoạn, dịch vụ trả về 503; nguy cơ sai lệch số dư tài khoản và tồn kho nếu không phục hồi chuẩn xác.
- **Owner:** Platform Database Administrator (DBA) & SRE On-Call Team
- **Verification Target:** RTO < 5 phút; RPO = 0s (Transactional parity: 100% khớp số dư tài khoản và idempotency ledgers, delta variance = 0).

---

## 2. Tiền điều kiện & Xác thực Bản sao lưu (Pre-flight Checks)
1. Xác định thời điểm xảy ra sự cố (Incident Timestamp $T_{incident}$).
2. Tìm snapshot hoặc WAL archive gần nhất trước $T_{incident}$:
   ```bash
   # Liệt kê danh sách snapshot sao lưu hợp lệ
   az backup recoverypoint list --resource-group rg-aks-platform-dev --backup-instance-name pg-backup-instance
   ```
3. Kiểm tra tính toàn vẹn của file backup (checksum SHA-256).

---

## 3. Quy trình Khôi phục Chuẩn (Step-by-Step Recovery Procedure)

### Bước 1: Kích hoạt Chế độ Bảo trì (Maintenance Mode / Traffic Shedding)
Ngăn chặn client tiếp tục ghi đè dữ liệu rác vào cluster:
```bash
kubectl scale deployment order-api --replicas=0 -n flash-sale
kubectl scale deployment bankops-api --replicas=0 -n banking
```

### Bước 2: Khôi phục Dữ liệu về Target Tạm thời (Point-in-Time Restore)
Thực hiện restore từ snapshot đã được chứng minh trong drill (`disaster-recovery-drill-PASS.md`):
```bash
# Thực thi script phục hồi tự động
python3 scripts/restore_database_snapshot.py \
    --snapshot-id "snap_pre_incident_latest" \
    --target-db "bankops_restored"
```

### Bước 3: Xác thực Tính toàn vẹn Dữ liệu Sau Khôi phục (Integrity Assertions)
Chạy script kiểm tra đối soát số dư tuyệt đối:
```bash
python3 scripts/verify_ledger_parity.py \
    --db-url "$RESTORED_DATABASE_URL" \
    --assert-zero-variance
```
*Yêu cầu bắt buộc*:
- Tổng số lượng Accounts khớp 100%.
- Tổng số Ledger Entries khớp 100%.
- Tổng số dư `SUM(Balance)` trước và sau phục hồi có delta = `0.0000`.

### Bước 4: Chuyển hướng Kết nối & Phục hồi Traffic
Cập nhật Kubernetes Secret trỏ sang database đã phục hồi và scale up workloads:
```bash
kubectl set env deployment/order-api ConnectionStrings__DefaultConnection="$NEW_CONNECTION_STRING" -n flash-sale
kubectl scale deployment order-api --replicas=2 -n flash-sale
kubectl rollout status deployment/order-api -n flash-sale
```

---

## 4. Nghiệm thu & Hậu kiểm (Post-Mortem & Evidence)
- Kiểm tra `/health/ready` của tất cả các pods (`HTTP 200`).
- Ghi nhận thời gian RTO thực tế vào post-mortem incident report theo mẫu `docs/incidents/`.
