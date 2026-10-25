# Bằng chứng Khép kín Hành trình Vận hành Kho & Phân quyền Chi nhánh (QuanLyKho)

## 1. Bài toán Doanh nghiệp & Rủi ro (Business Problem & Invariant)
Trong chuỗi vận hành kho và cửa hàng trà sữa (F&B / Retail Operations):
- **Xuất hàng theo FEFO (First Expired, First Out):** Nguyên liệu cận hạn sử dụng nhất phải được tự động ưu tiên xuất trước; hàng hết hạn bị chặn bán tự động, chỉ cho phép xuất hủy (spoilage) khi có lý do bắt buộc.
- **Tính toàn vẹn kiểm kê ca (Shift Stocktake):** Không cho phép 2 nhân viên mở trùng ca cùng thời điểm; phiếu điều chỉnh chỉ được chốt số dư sau quy trình kiểm duyệt (Maker-Checker).
- **Phân quyền và Phạm vi Chi nhánh (Branch Scoping):** Nhân viên cửa hàng không thể xem hoặc sửa đổi tồn kho của chi nhánh khác; Kiểm toán viên (Reviewer/Auditor) chỉ có quyền đọc dữ liệu đối soát, không thể tạo hoặc duyệt phiếu.
- **AI Agent Guardrails:** Mô hình AI tư vấn chỉ được đọc phiếu canonical đã lưu, tuyệt đối không có quyền tự động phê duyệt hoặc ghi sổ tồn.

## 2. Kết quả Thực tế trên PostgreSQL 16 Cô lập (cổng 5433)

Hệ thống đã chạy trên cơ sở dữ liệu `bankops_test` được dựng mới qua 28 phiên bản Alembic migrations (`alembic upgrade head`):

| Test Suite | Nội dung kiểm thử | Kết quả đo đạc |
| --- | --- | --- |
| `test_phase2b_fefo_outbound.py` | Phân loại xuất kho (sale, spoilage, transfer), trừ tồn theo FEFO qua nhiều lô, khóa dòng chống xuất âm | **8 passed, 0 failed** (100% green) |
| `test_phase1_stock_levels.py` | Ngưỡng an toàn kho, cảnh báo cận date, cảnh báo thiếu hàng theo chi nhánh | **15 passed, 0 failed** (100% green) |
| `test_approval_controls.py` | Cơ chế Maker-Checker, kiểm tra PIN giám sát, phòng chống tự duyệt phiếu | **10 passed, 0 failed** (100% green) |
| `test_shift_stocktake.py` | Kiểm kê ca, đối chiếu tồn sổ sách và tồn thực tế | **1 passed, 0 failed** (100% green) |
| `test_reviewer_readonly.py` | Kiểm toán viên đọc toàn bộ dữ liệu đối soát nhưng bị chặn 100% các thao tác ghi/duyệt | **8 passed, 0 failed** (100% green) |
| `test_inventory_alert_scope_unit.py` | Phạm vi lọc chi nhánh không bị mở rộng trái phép | **8 passed, 0 failed** (100% green) |
| `test_ai_assessment_canonical.py` | Ràng buộc AI Agent trên phiếu canonical, chặn trường giả mạo | **1 passed, 0 failed** (100% green) |
| `test_reserved_inventory_and_return.py` & catalog | Quản lý tồn giữ trước và trả hàng nhà cung cấp | **15 passed, 0 failed** (100% green) |

**Tổng cộng:** **66 test cases** kiểm thử toàn diện hành trình kho khép kín đều đạt **PASS 100%** trên PostgreSQL 16 thật.

## 3. Kết luận Cổng Chất lượng (Gate Verdict)
- Hành trình kho khép kín và phân quyền chi nhánh của QuanLyKho đạt trạng thái: **`LOCAL_VERIFIED`**.
- Đủ điều kiện để **ĐÓNG CỔNG GATE B** và chuyển cặp active sang **Gate C (OpsBridge + AKS Platform)**.
