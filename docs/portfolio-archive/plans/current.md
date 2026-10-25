# Kế Hoạch Hiện Tại (Current Plan) — ĐÃ HOÀN THÀNH

## Mục tiêu
Nâng cấp chất lượng toàn diện của Senior Engineering Monorepo từ mức nền tảng kỹ thuật lên chuẩn Portfolio ứng tuyển cao cấp cho ba vị trí:
1. Senior Software Engineer (Backend / Distributed Systems)
2. Software Architect / Principal Backend Engineer
3. Senior DevOps / Platform / SRE Engineer

## Tiến độ theo từng Gate

### Gate A: Retail + Ops Baseline [HOÀN TẤT]
- Retail: PR #13 merged, outlet authorization 30/30 ITs pass (`docs/evidence/retail-outlet-authorization-evidence.md`).
- Ops: 50/10 concurrency verified, 20 outbox compensation tests pass (`docs/evidence/2026-10-23-50-contenders-10-units.md`).

### Gate B: Retail + QuanLyKho Journey [HOÀN TẤT]
- Retail: Outlet boundary isolation và negative authorization pass.
- QuanLyKho: Khép kín toàn bộ hành trình kho FEFO, xuất hủy spoilage, kiểm kê ca, maker-checker approval controls (57+ tests pass, `docs/evidence/quanlykho-journey-evidence.md`).

### Gate C: Ops + AKS Platform trên Kind [HOÀN TẤT]
- Golden Path deployment trên cụm Kubernetes Kind 3 nodes (`local-platform`).
- Ordered sync waves (wave -3 -> PreSync migration -> wave 0 apps).
- Probes liveness & readiness, non-root security contexts.
- Diễn tập automated rollback drill: Injected bad image tag -> zero-downtime traffic serving on 2 replicas -> rollout undo thành công (`docs/evidence/kind-golden-path-rollback-evidence.md`).

### Gate D: QuanLyKho + AKS Platform SRE Drills [HOÀN TẤT]
- SRE Disaster Recovery Drill: Tự động snapshot -> phá hủy dữ liệu (`DROP TABLE ... CASCADE`) -> khôi phục trên DB cô lập. Đo lường RTO: 0.0748s (SLA < 300s), RPO: 0 (100% data parity, 0 balance variance) (`docs/evidence/disaster-recovery-drill-PASS.md`, `docs/runbooks/dr-recovery-drill.md`).
- 14 CI Validation Gates (47 assertions pass, `tests/test_gates.py`).

### Đóng gói Senior Portfolio [HOÀN TẤT]
- 3 Case Studies chuẩn phỏng vấn:
  1. `docs/interview-notes/case-study-1-concurrency-faults.md` (Senior SWE)
  2. `docs/interview-notes/case-study-2-ledger-architecture.md` (Software Architect)
  3. `docs/interview-notes/case-study-3-golden-path-sre.md` (Senior Platform / SRE)
- 3 Targeted CVs:
  1. `docs/cv/senior-swe.md`
  2. `docs/cv/software-architect.md`
  3. `docs/cv/senior-platform-engineer.md`
