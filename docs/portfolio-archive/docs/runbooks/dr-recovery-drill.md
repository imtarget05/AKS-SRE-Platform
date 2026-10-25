# Disaster Recovery & Business Continuity Runbook (PostgreSQL)

**Target Services:** `services/quanlykho` (PostgreSQL 16) & `services/opsbridge-flashsale` (PostgreSQL 15)  
**Drill Automated Script:** `platform/aks-sre-platform/scripts/disaster_recovery_drill.sh`  
**Verified Evidence:** `docs/evidence/disaster-recovery-drill-PASS.md`

---

## 1. Local Benchmark Measurements & Invariants

> **Drill Boundary Notice:** The figures below represent an isolated point-in-time snapshot and logical restore benchmark (`pg_restore`) of 4 synthetic ledger accounts and 4 entries on a clean PostgreSQL test container. They measure the raw restore execution step and do not represent full multi-workload operational recovery (which includes incident detection, alert routing, DNS traffic failover, and active consumer reconciliation).

| Objective | Target Benchmark | Measured Value (2026-10-24) | Status |
|---|:---:|:---:|:---:|
| **Table Restore Execution Time** | < 300s (5 minutes) | **0.0748s** | **BENCHMARK PASS** |
| **Recovery Point Objective (RPO)** | 0 data loss on committed snapshot | **0 data loss (100% parity)** | **BENCHMARK PASS** |
| **Account & Ledger Entry Match** | 100% row count match | 4/4 accounts, 4/4 entries | **BENCHMARK PASS** |
| **Balance Delta Check** | 0.0000 VND variance | 470,000,000.0000 == 470,000,000.0000 | **BENCHMARK PASS** |

---

## 2. Standard Operating Procedure (SOP)

### Phase 1: Automated Snapshot Generation
- Run daily cronjob (`cronjob-backup.yaml`) taking compressed custom dump (`pg_dump -Fc`).
- Generate SHA-256 integrity checksum alongside the dump.
- Encrypt snapshot using GPG before offsite replication (Cloudflare R2 / S3 cold storage).

### Phase 2: Catastrophic Loss Detection & Triage
1. Monitor alerts (`PostgresDown`, `PostgresHighErrorRate`, `DeadlockDetected`).
2. Identify affected namespace and volume mount.
3. Freeze incoming write traffic via ingress/route rerouting (serve 503 / read-only maintenance mode).

### Phase 3: Isolated Recovery & State Reconciliation
1. Provision isolated standby PostgreSQL instance.
2. Verify backup SHA-256 checksum against signed manifest.
3. Restore using `pg_restore --clean --if-exists`:
   ```bash
   pg_restore -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$TARGET_DB" "$BACKUP_FILE"
   ```
4. Execute audit query comparing `SUM(balance)` across all double-entry ledger accounts.
5. If checksum and balances match exactly, switch traffic back to the restored instance.
