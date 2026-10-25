# Senior Engineering Portfolio — Polyglot Monorepo

Một kho lưu trữ kỹ thuật chuẩn Senior Engineering (Senior SWE, Software Architect, Senior DevOps/Platform Engineer) giải quyết các bài toán rủi ro kinh doanh thực tế trong hệ thống phân tán, tài chính và quản lý chuỗi cung ứng.

---

## 1. Cấu trúc Dự án

```text
Senior-Engineering-Portfolio/
├── services/
│   ├── retail-finance/          # Java 17 / Spring Boot 3 / MySQL Core Banking Platform & Python Recon
│   ├── opsbridge-flashsale/     # .NET 10 / C# 13 Clean Architecture Flash-Sale Distributed System
│   └── quanlykho/               # Python 3.11 / FastAPI / PostgreSQL / Flutter Warehouse Ops
├── platform/
│   └── aks-sre-platform/        # Terraform / Kubernetes / ArgoCD / Policy-as-Code / Golden Path
├── docs/                        # Bằng chứng exact-SHA, ADRs, 3 Case Studies, Runbooks, CVs
│   ├── architecture/            # Kiến trúc hệ thống xuyên suốt & ADR tổng hợp
│   ├── evidence/                # Bằng chứng đo đạc: DB dumps, raw k6 profiles, test logs
│   ├── interview-notes/         # Phân tích trade-offs cho phỏng vấn Senior/Architect
│   ├── runbooks/                # FinOps, Incident Response, Disaster Recovery drills
│   └── cv/                      # 3 bộ CV chuyên biệt (Senior SWE, Architect, DevOps/Platform)
├── plans/                       # Kế hoạch & Lộ trình thực thi (roadmap.md, current.md)
├── tasks/                       # Task backlog & lessons learned
├── Makefile                     # Root build, test & verification runner
├── AGENTS.md                    # Unified coding conventions & active pair rules
├── STATUS.md                    # Snapshot trạng thái cổng chất lượng (Gates) & Claims
└── PHASES.md                    # Hợp đồng thực thi 6 phase chuẩn Senior Engineering
```

---

## 2. Ma trận Công nghệ Thực tế (Runtime Truth)

| Thành phần | Runtime & Ngôn ngữ | Framework & Storage | Vai trò & Bất biến Nghiệp vụ |
| --- | --- | --- | --- |
| **`services/retail-finance`** | **Java 17** (LTS)<br>Python 3.11 | Spring Boot 3.3<br>MySQL 8.0, Testcontainers | **Sở hữu Ledger:** Bất biến kế toán kép, mở tài khoản atomic, phân quyền truy cập theo Outlet. |
| **`services/opsbridge-flashsale`** | **.NET 10** (C# 13) | ASP.NET Core Web API<br>PostgreSQL 16, Redis 7 | **Sở hữu Order & Stock:** 50 tranh 10 không oversell, Outbox Compensation khi broker nack/lỗi. |
| **`services/quanlykho`** | **Python 3.11**<br>Dart / Flutter 3 | FastAPI, SQLAlchemy 2<br>PostgreSQL 16, Alembic | **Sở hữu Kho & Phê duyệt:** Nhập lô/HSD, xuất FEFO, kiểm kê ca, maker-checker, branch scoping. |
| **`platform/aks-sre-platform`** | **Bash / Python 3.11**<br>HCL / YAML | Terraform 1.9, Kustomize<br>Kubernetes, ArgoCD, Kind | **Sở hữu Golden Path:** Immutable image digest, migration trước deployment, probe, rollback tự động. |

---

## 3. Lệnh Điều phối (Root Makefile)

Tất cả các lệnh kiểm thử và quản lý được điều phối qua root `Makefile`:

```bash
# Xem trạng thái Monorepo và cặp active hiện hành
make status

# Chạy kiểm thử từng dịch vụ với đầy đủ Unit & Integration tests
make test-retail       # Java 17: Chạy toàn bộ Unit Tests & Testcontainers MySQL Integration Tests (mvn verify)
make test-ops          # .NET 10: Chạy 371 tests (Unit, Integration, Contract, Concurrency harness)
make test-quan         # Python 3.11: Chạy Pytest với DB PostgreSQL tạm cô lập (cổng 5433)
make test-platform     # Platform: Kiểm tra 47 assertions trên 14 cổng an toàn GitOps/Terraform

# Chạy toàn diện 4 hệ thống
make test-all
```

---

## 4. Nguyên tắc Làm việc (Engineering Conventions)
1. **Evidence-First:** Không tự claim "production-ready" khi chưa có bằng chứng exact-SHA trên môi trường xác định.
2. **Active Pair:** Tối đa hai thành phần được sửa cùng lúc (hiện tại: `services/retail-finance` + `services/opsbridge-flashsale`).
3. **Strict Data Ownership:** Không chia sẻ database chéo. Mọi giao tiếp liên hệ thống phải thông qua API hoặc Event contract.
4. **Code-Docs Integrity:** Tài liệu phải khớp 100% với mã nguồn thật.

## 5. Một thư mục làm việc, một Git repo

Làm việc từ thư mục gốc `Senior-Engineering-Portfolio/`. `services/opsbridge-flashsale/`, `services/quanlykho/` và `platform/aks-sre-platform/` là thư mục con của cùng repo, không có `.git` riêng. `services/retail-finance/` và `services/agent-hub/` cũng nằm trong repo này. Chạy `git status` và tạo commit từ thư mục gốc; CI chính ở `.github/workflows/monorepo-ci.yml`.

Ba checkout độc lập cũ được lưu tại `Downloads/.original-repos-backup-2026-10-24/` để đối chiếu và khôi phục, không phải nơi làm việc chính. File môi trường, cơ sở dữ liệu, cache và thư mục build không được nhập vào Git repo chung.
