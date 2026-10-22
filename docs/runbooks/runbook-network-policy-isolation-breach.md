# Runbook: NetworkPolicy Enforcement & Security Isolation Triage

## 1. Metadata & Classification
- **Trigger:** Phát hiện cảnh báo `NetworkPolicyViolation` hoặc traffic trái phép giữa các namespace (ví dụ Pod không được phép truy cập DB, hoặc egress ra Internet từ vùng cấm).
- **Severity:** P1 (Security / Compliance Breach)
- **Impact:** Vi phạm nguyên tắc Zero-Trust; nguy cơ rò rỉ dữ liệu (data exfiltration) hoặc tấn công leo thang đặc quyền giữa các tenant/microservices.
- **Owner:** Platform Security & SRE Team
- **Verification Target:** 100% gói tin trái phép bị chặn (timeout / dropped), chỉ cho phép traffic mang nhãn hợp lệ đi qua ingress/egress.

---

## 2. Mô hình Kiểm soát (Zero-Trust Model)
- **Mặc định Chặn (Default Deny):** Mọi namespace đều áp dụng policy `default-deny-ingress` và `default-deny-egress`.
- **Phân quyền tường minh (Explicit Allow):** Chỉ các Pod mang nhãn hợp lệ (`app.kubernetes.io/name`) và trong namespace cho phép mới được kết nối.

---

## 3. Quy trình Kiểm tra & Cô lập Sự cố (Diagnosis & Quarantine)

### Bước 1: Chạy kiểm tra tự động toàn diện (Probe Matrix)
Chạy script kiểm chứng chính thức của nền tảng:
```bash
bash scripts/test-network-policy-probe.sh
```

### Bước 2: Đối chiếu kết quả với ma trận chuẩn (Negative & Positive Controls)
| ID | Chiều | Nguồn | Đích | Kỳ vọng | Lệnh khắc phục nếu FAIL |
|---|---|---|---|---|---|
| **NEG-01** | Ingress | Pod unlabelled (default) | `sre-demo-api:80` | **Bị chặn (Timeout)** | Kiểm tra lại `ingress-networkpolicy.yaml` có sót selector không |
| **NEG-02** | Ingress | Pod `flashsale` namespace | `sre-demo-api:80` | **Bị chặn (Timeout)** | Đảm bảo `namespaceSelector` không để `matchLabels: {}` (all namespaces) |
| **NEG-04** | Egress | `sre-demo-api` | Internet `1.1.1.1:80` | **Bị chặn (Timeout)** | Cấm mở `0.0.0.0/0` trong egress rule của backend pods |
| **POS-01** | Ingress | `envoy-gateway` | `sre-demo-api:80` | **Cho phép (HTTP 200)** | Bật quyền ingress cho envoy pod label |

### Bước 3: Áp dụng lại Policy qua GitOps
Nếu phát hiện cấu hình bị drift hoặc bị sửa tay trái phép (manual tampering):
```bash
# Đồng bộ lại chính sách từ Argo CD (Source of Truth)
argocd app sync platform-network-policies --force --prune
```

---

## 4. Bằng chứng Kiểm chứng (Evidence Reference)
- Căn cứ: `docs/evidence/network-policy-enforcement-PASS.md`
- Kết quả kiểm chứng thực tế: 6/6 test cases đạt chuẩn (4 Negative controls dropped sạch sẽ, 2 Positive controls thông suốt).
