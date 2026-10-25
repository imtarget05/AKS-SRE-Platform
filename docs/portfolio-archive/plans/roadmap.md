# Lộ trình 12 Tuần — Senior Engineering Monorepo

## 1. Mục tiêu Tuyển dụng
- **Senior Software Engineer:** Tính đúng đắn của giao dịch phân tán, bất biến dữ liệu khi có sự cố, concurrency 50/10, transaction boundary.
- **Software Architect:** Thiết kế hệ thống Clean Architecture, Outbox Pattern, Ledger kép, phân quyền đa chi nhánh, chiến lược migration dữ liệu bền vững.
- **Senior DevOps/Platform Engineer:** Golden Path GitOps, Policy-as-Code, immutable image digest, diễn tập rollback và disaster recovery (RTO/RPO thực tế).

## 2. Bản đồ 6 Phase

| Phase | Thành phần Active | Rủi ro Doanh nghiệp Cần Giảm | Trạng thái Nghiệm thu |
| --- | --- | --- | --- |
| **Phase 0** | Monorepo Core | Phân mảnh checkout, sai lệch tài liệu/mã nguồn | ĐÃ HOÀN THÀNH (Baseline Monorepo established) |
| **Phase 1** | Retail + Ops | Tiền bị ghi trùng/thiếu; flash sale oversell | ĐANG THỰC HIỆN (Gate A) |
| **Phase 2** | Retail + Quan | Xem/sửa chéo dữ liệu outlet; sai lệch tồn kho | XẾP HÀNG (Gate B) |
| **Phase 3** | Ops + AKS | Mất đơn khi broker lỗi; release không lặp lại được | XẾP HÀNG (Gate C) |
| **Phase 4** | Quan + AKS | Khó khăn khi onboarding workload mới; không đo được restore | XẾP HÀNG (Gate D) |
| **Phase 5/6** | Toàn bộ Monorepo | Portfolio thiếu bằng chứng bảo vệ trong phỏng vấn | XẾP HÀNG (3 Case studies, 3 CVs) |
