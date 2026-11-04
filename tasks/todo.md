# Hàng đợi AI — portfolio cloud >90%

Xem [phân công, acceptance và lệnh verify](plan.md). Ma trận điểm: [`docs/evidence/2026-11-04-portfolio-gate-matrix.md`](../docs/evidence/2026-11-04-portfolio-gate-matrix.md). Mọi ô chỉ tick khi có evidence cùng release SHA.

## C0 — nền phát hành

- [ ] H0: chủ tài khoản rotate token đã lộ, cập nhật GitHub Secrets; xác nhận Azure state/cost/quota, tài khoản UAT và chủ ngân hàng.
- [ ] CI-1: ba repo có CI/Sonar scan thật xanh trên candidate SHA, không skip scanner.
- [ ] REL: tạo worktree/branch riêng cho từng AI, chốt file ownership và rollback target.

## C1 — hạ tầng và cloud release

- [ ] AKS-1: A13 policy toggle trên kind+Calico, raw log và teardown.
- [ ] AKS-2a: A16 đối chiếu state/quota/cost và nhận phê duyệt trước mutate.
- [ ] AKS-2b: A16 private-cluster runtime, GitOps, workload, policy và observability.
- [ ] AKS-2c: A16 Azure restore và rollback với before/after.
- [ ] QLK-1a: migration 034 và lỗi Redis, DB trống và snapshot cũ.
- [ ] QLK-1b: isolated API/PostgreSQL release cùng source SHA/image/revision.
- [ ] QLK-1c: backup, restore và rollback app/schema.
- [ ] CF-1a: persistence adapters cho identity/session/work item và storage.
- [ ] CF-1b: synthetic ACA/frontend cùng SHA/digest, IdP test tenant.
- [ ] CF-1c: 14 control cloud proof, negative controls và rollback.

## C2 — hành trình và phê duyệt

- [ ] QLK-2a: CATALOG và RECEIPT.
- [ ] QLK-2b: APPROVAL và FEFO.
- [ ] QLK-2c: DAMAGE và ADJUST.
- [ ] QLK-3a: SHIFT-OPEN và SHIFT-COUNT.
- [ ] QLK-3b: SHIFT-HANDOFF và SHIFT-LOCK.
- [ ] QLK-3c: ALERT-LOW và ALERT-EXPIRY.
- [ ] QLK-3d: ALERT-VARIANCE và ALERT-STREAM.
- [ ] QLK-4a: REPORT-XNT và REPORT-TOP.
- [ ] QLK-4b: REPORT-HISTORY và RBAC.
- [ ] QLK-4c: AUDIT.
- [ ] QLK-5: OFFLINE-NATIVE, PLATFORMS trên thiết bị và web live API.
- [ ] CF-2a: G01 IdP/lifecycle và G02 data/model, mỗi gate có owner/artifact riêng.
- [ ] CF-2b: G03 core contract và G04 privacy/security, mỗi gate có owner/artifact riêng.
- [ ] CF-2c: G05 DR và G06 staff workflow, mỗi gate có owner/artifact riêng.
- [ ] CF-2d: G07 delayed outcomes và G08 operational quality, mỗi gate có owner/artifact riêng.

## C3 — chốt

- [ ] REL: ma trận 14+21+22 ID có raw evidence gắn SHA/digest/revision, điểm >90%, CI links, cost và rollback.
- [ ] Chủ hệ thống: quyết định go-live riêng cho AKS, QuanLyKho và CreditFlow; chữ ký/điều kiện còn mở.
