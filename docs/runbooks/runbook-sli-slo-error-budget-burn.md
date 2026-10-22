# Runbook: SLI/SLO Error Budget Multi-Window Burn Rate Alert

## 1. Metadata & Classification
- **Trigger:** Prometheus Alert `SLOHighErrorRateBurn` (Burn Rate >= 14.4x over 5m/1h or >= 6.0x over 30m/6h)
- **Severity:** P1 (Fast Burn: 14.4x) / P2 (Slow Burn: 6.0x)
- **Impact:** Dịch vụ vi phạm cam kết 99.9% Availability SLO; nguy cơ cạn kiệt Error Budget của tháng trong vòng 24–48 giờ; khách hàng gặp lỗi HTTP 5xx.
- **Owner:** SRE On-Call Engineer & Core Backend Team
- **Verification Target:** Tỉ lệ lỗi 5xx giảm về < 0.1%, Availability phục hồi >= 99.90%, Burn Rate giảm về < 1.0x.

---

## 2. Mathematical Rationale (Google SRE Multi-Burn-Rate)
Công thức tính Burn Rate:
$$\text{Burn Rate} = \frac{\text{Observed Error Ratio}}{1 - \text{SLO Target}} = \frac{\text{5xx Errors} / \text{Total Requests}}{0.001}$$

- **Fast Burn (14.4x):** Tiêu thụ 2% Error Budget trong 1 giờ. Cần can thiệp khẩn cấp (Page ngay).
- **Slow Burn (6.0x):** Tiêu thụ 5% Error Budget trong 6 giờ. Cần mở ticket điều tra trong ngày làm việc.

---

## 3. Quy trình Xử lý Sự cố (Triage & Remediation Steps)

### Bước 1: Xác nhận mức độ khẩn cấp (Immediate Triage)
Chạy lệnh kiểm tra tỉ lệ lỗi và pod status:
```bash
# 1. Kiểm tra pod status trong namespace
kubectl get pods -n sre-demo -l app.kubernetes.io/name=sre-demo-api -o wide

# 2. Xem logs 5xx gần nhất
kubectl logs -n sre-demo -l app.kubernetes.io/name=sre-demo-api --tail=100 | grep -E "HTTP 5[0-9]{2}|ERROR|Exception"

# 3. Kiểm tra Envoy Gateway ingress traffic
kubectl logs -n envoy-gateway-system -l gateway.envoyproxy.io/owning-gateway-name=default-gateway --tail=100
```

### Bước 2: Phân loại nguyên nhân (Root Cause Isolation)
- **Trường hợp A: Quá tải CPU / Memory dẫn đến OOMKilled:**
  Kiểm tra: `kubectl describe pod -n sre-demo <pod-name> | grep -E "OOMKilled|Restart Count"`
  Khắc phục: Tăng memory limits hoặc kích hoạt HPA/KEDA scale-out.
- **Trường hợp B: Dependency Down (Database / Redis timeout):**
  Kiểm tra kết nối: `kubectl exec -it -n sre-demo <pod-name> -- nc -zv <db-host> <db-port>`
  Khắc phục: Chuyển hướng traffic hoặc bật chế độ Graceful Degradation (Fail-closed / Cached fallback).
- **Trường hợp C: Bản deploy mới gây lỗi (Bad Release):**
  Khắc phục khẩn cấp: Rollback bản release trước đó qua Argo CD:
  ```bash
  argocd app rollback sre-demo-api --revision <previous-stable-commit>
  ```

### Bước 3: Xác nhận phục hồi (Verification)
Chạy script đo đạc SLI baseline:
```bash
bash scripts/measure-sli-baseline.sh
```
Kết quả đạt chuẩn: `Observed 5xx Errors: 0`, `Availability SLI: 100%`, `Burn Rate: 0.0x`.
