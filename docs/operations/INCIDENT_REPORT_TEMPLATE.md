# Incident Report Template — Báo cáo sự cố

Áp dụng cho: **AKS-SRE-Platform** và **QuanLyKho**

## 1. Thông tin chung

| Trường | Giá trị |
|--------|---------|
| Mã sự cố | INC-<YYYYMMDD>-<NNN> |
| Thời điểm phát hiện | <YYYY-MM-DDTHH:MM:SSZ> |
| Thời điểm bắt đầu xử lý | <YYYY-MM-DDTHH:MM:SSZ> |
| Thời điểm khôi phục | <YYYY-MM-DDTHH:MM:SSZ> |
| Thời điểm kết thúc postmortem | <YYYY-MM-DDTHH:MM:SSZ> |
| Mức độ severity | P1 / P2 / P3 |
| Người báo cáo | <tên> |
| Người xử lý (Incident Commander) | <tên> |
| Dịch vụ affected | QuanLyKho / AKS-SRE-Platform / Cả hai |

## 2. Tóm tắt sự cố

<Mô tả ngắn gọn: dịch vụ nào bị ảnh hưởng, triệu chứng gì, thời gian downtime, số user affected>

## 3. Timeline chi tiết

| Thời gian | Hành động | Người thực hiện | Ghi chú |
|-----------|-----------|-----------------|---------|
| T+0 | Phát hiện bất thường qua alert/monitoring | <tên> | Alert: <tên alert> |
| T+5 | Bắt đầu điều tra | <tên> | Kiểm tra pod status, logs |
| T+10 | Xác định root cause | <tên> | Lỗi: <mô tả> |
| T+15 | Thực hiện mitigate | <tên> | Rollback / kill transaction / scale up |
| T+20 | Dịch vụ đã phục hồi | <tên> | Verify: health check HTTP 200 |
| T+60 | Kết thúc postmortem | <tên> | Ghi action items |

## 4. Tác động (Impact)

| Chỉ số | Giá trị |
|--------|---------|
| Thời gian downtime | <X> phút |
| Số user affected | <X> người/lượt |
| Error rate cao nhất | <X>% |
| Latency p95 cao nhất | <X> ms |
| Loss estimation | <mô tả nếu có> |

## 5. Nguyên nhân gốc (Root Cause)

### 5.1 Những gì đã xảy ra

<Mô tả chi tiết chuỗi sự kiện dẫn đến sự cố>

### 5.2 Root Cause (5 Whys)

1. **Tại sao sự cố xảy ra?** <câu trả lời>
2. **Tại sao vấn đề đó xảy ra?** <câu trả lời>
3. **Tại sao vấn đề thứ hai xảy ra?** <câu trả lời>
4. **Tại sao vấn đề thứ ba xảy ra?** <câu trả lời>
5. **Tại sao vấn đề thứ tư xảy ra?** <câu trả lời>

**Root cause:** <kết luận cuối cùng>

### 5.3 Yếu tố đóng góp

- <yếu tố 1>
- <yếu tố 2>
- <yếu tố 3>

## 6. Bằng chứng

| Loại | Đường dẫn/Tài liệu | Mô tả |
|------|-------------------|-------|
| Logs | <link/file> | <mô tả> |
| Metrics | <link/Grafana dashboard> | <mô tả> |
| Traces | <link/Tempo> | <mô tả> |
| Screenshots | <link/file> | <mô tả> |
| SQL queries | <link/file> | <mô tả> |

## 7. Xử lý đã thực hiện (Mitigation)

| Hành động | Thời gian | Người thực hiện | Kết quả |
|-----------|-----------|-----------------|---------|
| Rollback deployment | T+15 | <tên> | Thành công / Thất bại |
| Kill transaction dài hạn | T+18 | <tên> | Thành công / Thất bại |
| Scale up pod | T+20 | <tên> | Thành công / Thất bại |

## 8. Kiểm chứng phục hồi (Verification)

| Kiểm tra | Lệnh/Cách kiểm tra | Kết quả |
|----------|-------------------|---------|
| Health check | `curl -f /api/v1/health/live` | HTTP 200 |
| Pod ready | `kubectl get pods` | READY=1/1 |
| Argo CD sync | `kubectl get application` | Synced/Healthy |
| Error rate | Grafana dashboard | < 0.1% |
| Latency p95 | Grafana dashboard | < 200ms |

## 9. Hành động phòng ngừa (Action Items)

| # | Hành động | Owner | Deadline | Trạng thái |
|---|-----------|-------|----------|------------|
| 1 | <mô tả hành động phòng ngừa> | <tên> | <ngày> | Open / In Progress / Done |
| 2 | <mô tả hành động phòng ngừa> | <tên> | <ngày> | Open / In Progress / Done |
| 3 | <mô tả hành động phòng ngừa> | <tên> | <ngày> | Open / In Progress / Done |

## 10. Bài học rút ra

| Loại | Bài học |
|------|---------|
| Giữa làm | <gì đã làm tốt trong sự cố này> |
| Cần cải thiện | <gì cần cải thiện cho lần sau> |
| Gap monitoring | <chỉ số thiếu gì nên thêm vào dashboard> |
| Gap runbook | <tình huống nào chưa có runbook> |

---

## Ký tên

| Vai trò | Tên | Ký | Ngày |
|---------|-----|----|------|
| Incident Commander | | | |
| SRE Lead | | | |
| Backend Maintainer | | | |