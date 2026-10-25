# Quick Interview Defense Cheatsheet
## Bản Tóm Tắt 1 Trang Ôn Tập 10 Phút Trước Khi Vào Phỏng Vấn Senior

---

## 1. 30-Second Elevator Pitch (Giới Thiệu Dự Án Trong 30 Giây)

> *"Đây là một hệ thống bán lẻ và ngân hàng lõi quy mô lớn được thiết kế để giải quyết bài toán chống oversell trong các đợt flash sale lưu lượng cao, đảm bảo tính toàn vẹn sổ cái tài chính kép, và thiết lập đường ống GitOps Golden Path tự động hóa toàn diện trên Kubernetes. Hệ thống gồm 4 subsystem độc lập viết bằng Java 17, .NET 10, Python 3.11 và Terraform, được bảo vệ bằng hơn 1,100 automated tests và đo lường bằng chứng thực nghiệm trực tiếp trên Azure Cloud và cụm Kubernetes."*

---

## 2. Thông Số Kỹ Thuật Trọng Tâm (Monorepo At A Glance)

| Subsystem | Tech Stack | Role / Nhiệm Vụ | Cơ Sở Dữ Liệu | Số Lượng Test |
|---|---|---|---|---|
| **Retail Finance** | Java 17, Spring Boot, Maven | Core Banking & Ledgers | MySQL 8 | **76 tests** (28 unit, 31 IT Testcontainers, 17 recon) |
| **OpsBridge** | C# 13, .NET 10, ASP.NET Core | Flash Sale Order Reliability | PostgreSQL 16 + Redis | **371 tests** (Unit, IT, Concurrency Harness) |
| **QuanLyKho** | Python 3.11, FastAPI, Poetry | Warehouse Ops (FEFO, Stocktake) | PostgreSQL 16 | **714 tests** (Pytest, Alembic 001..028) |
| **AKS Platform** | Terraform 1.9, Azure, Argo CD | SRE Golden Path & GitOps | Azure Cloud / Kind | **47 gate assertions** (`test_gates.py`) |
| **TỔNG CỘNG** | **Monorepo Thống Nhất** | **End-to-End Retail Platform** | **Polyglot Storage** | **1,161/1,161 tests PASS (100%)** |

---

## 3. Bảng Số Liệu Bằng Chứng Vàng (The "Golden Metrics" Table)

| Chỉ Số | Con Số Thực Nghiệm | Bằng Chứng Kỹ Thuật |
|---|---|---|
| **Oversold Units** | **0 đơn vị** | k6 50 VU burst tranh chấp 10 items |
| **P95 Latency** | **132.2 ms** | Đo tải qua Envoy Gateway dưới áp lực đồng thời |
| **Disaster Recovery RTO** | **0.787 giây** (786.52 ms) | Khôi phục thảm họa toàn phần DB trên Kubernetes |
| **Disaster Recovery RPO** | **4 giây (5 đơn delta)** | Giải thích vì sao cold snapshot có delta loss |
| **Rollback Duration** | **509 ms** | Tự động rollback khi tiêm image lỗi (100% 200 OK) |
| **Cloud Cluster Live** | **AKS v1.36.5** | Provisioned tại `rg-aks-platform-dev` (East Asia) |
| **Cloud Auth Method** | **100% OIDC / Secretless** | Microsoft Entra ID Federated Credentials |

---

## 4. Năm "Cái Bẫy" Cần Tránh Khi Trả Lời Phỏng Vấn (5 Traps to Avoid)

1. ❌ **Bẫy 1:** Nói *"Em dùng pg_dump tự động nên RPO luôn bằng 0"*.
   - ✅ **Cách nói đúng:** *"pg_dump là cold snapshot, chỉ đảm bảo dữ liệu tới thời điểm snapshot. Khoảng thời gian từ snapshot đến thảm họa vẫn có thể mất dữ liệu (như trong bài test của em là mất 5 đơn trong 4s). Để RPO = 0 cần Continuous WAL Archiving hoặc Synchronous Replication."*
2. ❌ **Bẫy 2:** Nói *"Hệ thống của em đảm bảo Zero-Downtime 100% trong mọi tình huống"*.
   - ✅ **Cách nói đúng:** *"Hệ thống được thiết kế với Rolling Updates (maxSurge=1, maxUnavailable=0) và PDB. Chúng em đo được 0 request lỗi trong lúc rolling update ứng dụng, nhưng nếu thảm họa hạ tầng DB xảy ra thì RTO đo được là 0.787s để phục hồi."*
3. ❌ **Bẫy 3:** Nói *"Em lưu Azure Client Secret trong GitHub Actions Secret"*.
   - ✅ **Cách nói đúng:** *"Em dùng Workload Identity Federation (OIDC) không lưu bất kỳ password hay secret nào trong repo; GitHub Actions tự mint token ngắn hạn 1 giờ với Microsoft Entra ID."*
4. ❌ **Bẫy 4:** Nói *"Database nào cũng như nhau, em dùng SQLite/H2 để test integration cho nhanh"*.
   - ✅ **Cách nói đúng:** *"Em dùng Testcontainers MySQL 8 và PostgreSQL 16 thật vì H2 không tái hiện được deadlock, dialect khác biệt và transaction isolation level của database thật."*
5. ❌ **Bẫy 5:** Trả lời chung chung lý thuyết mà không viện dẫn bằng chứng.
   - ✅ **Cách nói đúng:** *"Luôn dẫn câu chuyện: Vấn đề kinh doanh $\rightarrow$ Rủi ro kỹ thuật $\rightarrow$ Giải pháp thiết kế $\rightarrow$ Con số đo lường thực tế."*
