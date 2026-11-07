# Phase 15 — Disaster recovery drill

Goal: full rebuild + DB restore with measured RPO/RTO.

Steps:
1. Capture pg_dump (custom format) of all service schemas.
2. Destroy validation namespace + PVCs.
3. Re-apply manifests (kustomize) + restore DB.
4. Re-run smoke (healthz, /api/payments).
5. Record RPO (last committed transaction) and RTO (wall clock).

RPO target: 0s for committed snapshot. RTO target: <= 10 min for validation env.
