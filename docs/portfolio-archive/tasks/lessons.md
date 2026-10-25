# Bài học Kinh nghiệm & Đúc kết Kỹ thuật (Lessons Learned)

1. **Code-Docs Alignment:**
   - Không được để xảy ra sai lệch giữa tài liệu kiến trúc và mã nguồn thực tế (ví dụ khai báo Java 21/.NET 9 trong khi pom.xml dùng Java 17 và csproj dùng net10.0). Đây là tiêu chí đánh giá sự tỉ mỉ của Senior Engineer.
2. **Monorepo Automation:**
   - Lệnh `make test-all` phải kiểm thử mọi thành phần hoặc thông báo lý do rõ ràng; không được âm thầm bỏ qua bất kỳ service nào.
   - Thư mục root phải có GitHub Actions CI với path-filtering để khi push lên Git remote, toàn bộ các job được kích hoạt tương ứng.
3. **Database Test Isolation:**
   - QuanLyKho có cơ chế guard trong `conftest.py` ngăn chặn chạy test trên DB dev (`bankops`) mà không có hậu tố `_test`. Luôn sử dụng `bankops_test` trên cổng tách biệt (vd: 5433).
