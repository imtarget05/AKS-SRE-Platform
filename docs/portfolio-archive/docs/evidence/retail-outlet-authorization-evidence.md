# Bằng chứng Kiểm thử Phân quyền Outlet & Schema Upgrade V2 (Retail Finance)

## 1. Bài toán Doanh nghiệp & Rủi ro (Business Problem & Invariant)
Trong mô hình bán lẻ chuỗi nhiều cửa hàng (Outlets), nhân viên thu ngân (POS Cashier) tại Cửa hàng A không được phép:
- Đọc thông tin tài khoản hoặc số dư của khách hàng thuộc Cửa hàng B.
- Thực hiện giao dịch nạp/rút tiền trên tài khoản thuộc Cửa hàng B.
- Replay idempotency key để xem hoặc can thiệp giao dịch của Cửa hàng B.
- Sử dụng JWT cũ (stale token) sau khi đã bị vô hiệu hóa hoặc hạ quyền trong cơ sở dữ liệu.

## 2. Kết quả Thực tế trên MySQL 8 Testcontainers (Integration Test Execution)

Chạy trên MySQL 8.0 container thực tế trong suite kiểm thử:
- Lệnh: `mvn test -Dtest=OutletAuthorizationIT,AccountOutletUpgradeIT,StaleJwtAuthorizationIT,AccountOpeningIT`
- Kết quả: **30 tests passed, 0 failures, 0 errors**.

| Test Case | Kịch bản kiểm thử | Hành vi nghiệp vụ chứng minh | Kết quả |
| --- | --- | --- | --- |
| `staffCannotOpenOrAttributeOpeningMovementToAnotherOutlet` | Staff outlet A mở tài khoản với outlet code B | Trả về `403 Forbidden`, không có tài khoản hay bút toán nào được ghi | **PASS** |
| `staffCannotReadForeignAccountOrTransactionOrPostOrReplay` | Token outlet A cố đọc tài khoản/giao dịch hoặc replay request của outlet B | Từ chối truy cập `403 Forbidden`, che giấu toàn bộ PII và thông tin khách hàng | **PASS** |
| `unresolvedLegacyAccountIsFailClosedForStaffButVisibleToOperations` | Tài khoản V1 cũ có `outlet_id = NULL` sau migration | POS staff bị chặn truy cập (Fail-Closed). Chỉ OPS/Admin có quyền tra cứu | **PASS** |
| `zeroOpeningBalanceStillRecordsOwnerAndDeniesOtherOutlet` | Mở tài khoản với số dư ban đầu bằng 0 | Vẫn ghi nhận outlet sở hữu chính xác, chặn truy cập từ outlet khác | **PASS** |
| `demotedOrDisabledOpsCannotUsePreviouslyIssuedTokenForLedgerOrAudit` | Nhân viên bị disable/demote trong DB nhưng JWT chưa hết hạn | Kiểm tra authoritative user state trong DB trên mỗi request, lập tức từ chối `403` | **PASS** |
| `leavesAllLegacyAccountsUnresolvedEvenAfterCashierReassignment` | Nâng cấp schema Flyway `V1 -> V2` | Schema thêm cột `outlet_id` nullable, giữ nguyên dữ liệu cũ mà không tự ý gán sai outlet | **PASS** |

## 3. Kết luận Cổng Chất lượng (Gate Verdict)
- Tính năng phân quyền theo Outlet và tiến hóa Schema V2 đạt trạng thái: **`LOCAL_VERIFIED`** (chứng minh bền vững trên MySQL 8 thật).
