# Runbook: Node Maintenance & PodDisruptionBudget (PDB) Drain Operations

## 1. Metadata & Classification
- **Trigger:** Kỹ sư SRE thực hiện nâng cấp phiên bản Kubernetes Node Pool (OS upgrade, Kernel security patch) hoặc nhận cảnh báo node hardware failure.
- **Severity:** P2 (Planned Maintenance) / P1 (Emergency Node Eviction)
- **Impact:** Nguy cơ downtime nếu tất cả replicas của một service bị evict đồng thời; rớt kết nối của in-flight requests nếu CNI/Endpoints không cập nhật kịp thời.
- **Owner:** Platform & SRE Operations Team
- **Verification Target:** 100% in-flight availability (0 dropped requests, 0 HTTP 5xx errors) trong suốt quá trình drain.

---

## 2. Tiền điều kiện An toàn (Pre-flight Checks)
Trước khi drain bất kỳ node nào:
1. Đảm bảo `PodDisruptionBudget` tồn tại và hợp lệ:
   ```bash
   kubectl get pdb -A
   # Xác nhận minAvailable hoặc maxUnavailable cho sre-demo-api và flashsale workloads
   ```
2. Đảm bảo cluster còn đủ node dung lượng dự phòng để tiếp nhận Pod di dời:
   ```bash
   kubectl top nodes
   kubectl describe nodes | grep -A 5 "Allocated resources"
   ```

---

## 3. Quy trình Thực thi Chuẩn (Step-by-Step Procedure)

### Bước 1: Cordon node (Ngăn chặn scheduler phân bổ pod mới)
```bash
kubectl cordon <target-node-name>
# Xác thực trạng thái node chuyển sang SchedulingDisabled
kubectl get nodes
```

### Bước 2: Thực thi Drain có kiểm soát PDB
Sử dụng script drill tự động hoặc lệnh thủ công chuẩn:
```bash
# Thực thi drain với cờ an toàn
kubectl drain <target-node-name> \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --force=false \
  --timeout=180s
```

*Cơ chế tự vệ:* Nếu lệnh drain vi phạm `PDB` (ví dụ pod còn lại duy nhất chưa Ready trên node khác), lệnh drain sẽ bị API server từ chối với lỗi:
`Cannot evict pod as it would violate the pod's disruption budget.`

### Bước 3: Theo dõi lưu lượng In-Flight
Chạy synthetic probe liên tục trong khi node đang drain:
```bash
bash scripts/pdb-drain-drill.sh
```

### Bước 4: Hoàn tất bảo trì & Uncordon
Sau khi node được vá lỗi / reboot thành công:
```bash
kubectl uncordon <target-node-name>
# Xác nhận node trở lại trạng thái Ready và tiếp nhận pods
kubectl get nodes
```

---

## 4. Bằng chứng Kiểm chứng (Evidence Reference)
- Căn cứ: `docs/evidence/pdb-drain-drill-PASS.md`
- Kết quả kiểm chứng thực tế: 40/40 request thành công (100% HTTP 200), thời gian drain 7.747s, không rớt bất kỳ request nào.
