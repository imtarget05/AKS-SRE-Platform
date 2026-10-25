# ADR 025 — Canonical Repositories là Nguồn Mã Nguồn và Cơ Chế Đồng Bộ Monorepo

**Status:** Accepted.

## Bối cảnh và vấn đề kỹ thuật (Context & Problem Statement)

Dự án danh mục kỹ sư Senior (Senior Engineering Portfolio) bao gồm 4 hệ thống độc lập và một Agent Hub:
1. `retail-finance-core-platform` (Java 17 / Spring Boot 3 / MySQL / Python)
2. `OpsBridge` (`FlashSale-Backend`, .NET 10 / C# 13 / PostgreSQL / Redis / RabbitMQ)
3. `QuanLyKho` (Python 3.11 / FastAPI / Alembic / PostgreSQL 16)
4. `AKS-SRE-Platform` (Terraform / Gateway API / KEDA / Argo CD / Agent Hub)
5. `Senior-Engineering-Portfolio` (Monorepo tích hợp và bằng chứng)

Trước đây, mã nguồn được sao chép thủ công (copy-paste) giữa các repo canonical và monorepo, dẫn đến các sai lệch nghiêm trọng (drift):
- Monorepo sửa bản vá Testcontainers hoặc single-event recovery nhưng canonical repo không có, khiến CI canonical đỏ dù monorepo xanh.
- Monorepo tồn tại mã cũ (ví dụ: Agent Hub executor gọi bulk `/api/outbox/requeue` với Staff JWT) khác hoàn toàn với thiết kế an toàn của canonical repo.
- Báo cáo và bằng chứng dẫn sai SHA giữa commit snapshot của monorepo và commit thật trên canonical remote.

Cần một quyết định kiến trúc xác lập rõ ràng quyền sở hữu mã nguồn, ranh giới trách nhiệm, và cơ chế đồng bộ tự động chống sai lệch.

## Quyết định kiến trúc (Decision)

### 1. Phân định quyền sở hữu (Source-of-Truth Hierarchy)
- **Canonical Repositories là NGUỒN MÃ NGUỒN DUY NHẤT (Single Source of Truth):**
  - Mọi thay đổi logic nghiệp vụ, migration, API endpoint, security policy, và workload test PHẢI được phát triển, commit, mở Pull Request và chạy CI thành công trên canonical repository tương ứng.
  - Không được commit tính năng mới trực tiếp vào monorepo mà chưa qua canonical PR/CI.
- **Monorepo `Senior-Engineering-Portfolio` là BẢN TÍCH HỢP VÀ BẰNG CHỨNG (Integration & Evidence Monorepo):**
  - Monorepo phản chiếu (mirror) mã nguồn từ canonical repos tại các exact SHA đã được kiểm chứng.
  - Monorepo chịu trách nhiệm: chạy cross-cutting evaluation (`tests/evals`), kiểm thử tích hợp chéo hệ thống, lưu trữ tài liệu tổng thể (`PHASES.md`, `STATUS.md`, ADRs), và tạo báo cáo đối chiếu bằng chứng (evidence aggregation).

### 2. Ma trận sở hữu thành phần (Component Ownership Matrix)

| Thành phần | Canonical Repo | Remote URL | Đường dẫn trong Monorepo | Đội ngũ / Vai trò sở hữu |
| --- | --- | --- | --- | --- |
| Retail Finance | `retail-finance-core-platform` | `https://github.com/imtarget05/retail-finance-core-platform.git` | `services/retail-finance/` | Retail Core Team (Senior Java SWE) |
| OpsBridge / FlashSale | `FlashSale-Backend` (`OpsBridge`) | `https://github.com/imtarget05/FlashSale-Backend.git` | `services/opsbridge-flashsale/` | OpsBridge Team (Senior .NET SWE) |
| QuanLyKho | `QuanLyKho` | `https://github.com/imtarget05/QuanLyKho.git` | `services/quanlykho/` | QuanLyKho Team (Senior Python SWE) |
| AKS SRE Platform & Hub | `AKS-SRE-Platform` | `https://github.com/imtarget05/AKS-SRE-Platform.git` | `platform/aks-sre-platform/`, `services/agent-hub/` | Platform SRE & Security Lead |
| Monorepo Integrator | `Senior-Engineering-Portfolio` | `https://github.com/imtarget05/Senior-Engineering-Portfolio.git` | Root, `docs/`, `tests/evals/` | Monorepo Lead Integrator |

### 3. Cơ chế đồng bộ có xác thực Hash (Hash-Verified Synchronization Mechanism)

Để chấm dứt việc copy tay không kiểm soát, thiết lập cơ chế đồng bộ:
1. **Metadata Manifest (`canonical-manifest.json`):** Monorepo duy trì file manifest lưu trữ exact commit SHA, remote URL, và component tree-hash của từng canonical repo.
2. **Kịch bản kiểm tra sai lệch tự động (`scripts/check-canonical-drift.sh`):**
   - Kiểm tra xem mã trong `services/*` và `platform/*` của monorepo có khớp chính xác với tree hash tương ứng của canonical repo tại exact SHA hay không.
   - Phát hiện các thay đổi "mồ côi" (unvetted commits) được thêm trực tiếp vào monorepo.
3. **Drift Gate trong Monorepo CI:**
   - Khi có thay đổi trong `services/*` hoặc `platform/*`, CI monorepo sẽ chạy bước xác thực: commit SHA được khai báo phải tồn tại trên remote của canonical repo và cây thư mục phải khớp hash.

## Hệ quả & Đánh giá đánh đổi (Consequences & Trade-offs)

- **Ưu điểm:**
  - Bảo toàn tính độc lập của từng dự án thành phần (có thể chạy độc lập, phỏng vấn độc lập theo từng domain chuyên môn).
  - Ngăn ngừa hoàn toàn hiện tượng "code monorepo chạy được nhưng canonical CI hỏng" hoặc ngược lại.
  - Mọi claim trong CV và tài liệu đều gắn với exact SHA trên canonical repo và run CI thật của canonical repo.
- **Đánh đổi / Thách thức:**
  - Cần thực hiện quy trình hai bước: (1) Merge và verify trên canonical repo, (2) Cập nhật manifest và mirror sang monorepo.
  - Tuyệt đối không được commit vội trực tiếp vào monorepo.
