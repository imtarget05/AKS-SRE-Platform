# Task Hiện Tại: Hiệu chỉnh Phản ánh Trung thực & Tập trung Gate 1 (Retail + Ops)

## Cặp Active hiện hành duy nhất
**`services/retail-finance` + `services/opsbridge-flashsale`** (Phase 1 / Gate 1).

---

## 1. Các hạng mục hiệu chỉnh đã hoàn thành
- [x] **Thu hồi các claim vượt quá bằng chứng:** Rút bỏ claim "Zero downtime" và "RTO 0.0748s / RPO 0 cho 2 workload" khỏi 3 bản CV (`docs/cv/`), case study và runbook.
- [x] **Hiệu chỉnh `STATUS.md`:** Đưa trạng thái Gate 1 về `IN_PROGRESS / PARTIAL`, chuyển Gate 2–4 về `CHƯA ĐẠT (QUEUED)`.
- [x] **Loại bỏ `|| true` che giấu lỗi:** Sửa `Makefile` (`test-retail`) và `.github/workflows/monorepo-ci.yml` để các bước kiểm thử Python fail-fast thực sự.
- [x] **Vá lỗi bảo mật và đường dẫn trong AKS Deploy:**
  - Sửa `platform/aks-sre-platform/.github/workflows/aks-deploy.yml`: Xóa bỏ trigger tự động chạy `terraform apply` khi push `main`. Chuyển sang kích hoạt thủ công (`workflow_dispatch`).
  - Xóa bỏ các đường dẫn cá nhân hardcoded (`/Users/mainguyenbinhtan/...`) trong `aks-deploy.yml`, `rebuild-aks.sh`, `portfolio_knowledge_retriever.py`.

---

## 2. Nhiệm vụ Gate 1 đang tiến hành
- [x] **Retail Finance:** Chạy sạch toàn bộ test Java (30 integration tests MySQL 8 Testcontainers) và Python recon tests (17 passed, không dùng `|| true`).
- [ ] **OpsBridge FlashSale:** Kiểm tra trạng thái checkpoint `bcf5ba9` (outbox compensation), chạy 371 xUnit tests trên exact SHA, ghi nhận raw artifact đối soát.
- [ ] **Tạo commit sạch cho Gate 1 baseline** và chuẩn bị điều kiện chuyển sang Gate 2 khi người dùng duyệt.
