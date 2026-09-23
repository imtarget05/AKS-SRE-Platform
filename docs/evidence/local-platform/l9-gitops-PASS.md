# L9 — GitOps Forward Deployment & Rollback via Argo CD — PASS

**Date:** 2026-09-23  
**Cluster:** `kind-local-platform` (Kubernetes v1.36.1)  
**Azure mutated:** NO — local kind only.  

## L9.1 & L9.2 — Argo CD Application Management

Argo CD manages both project repositories independently under the `portfolio` AppProject:

```text
Application: flashsale
  Source Repo: https://github.com/imtarget05/FlashSale-Backend.git
  Path: infrastructure/kubernetes/overlays/local
  Destination: in-cluster, namespace: flashsale
  Sync Status: Synced
  Health: Healthy (11/11 resources)

Application: legacyapp
  Source Repo: https://github.com/imtarget05/Productionized-LegacyApp.git
  Path: infrastructure/kubernetes/overlays/local
  Destination: in-cluster, namespace: legacyapp
  Sync Status: Synced
  Health: Healthy (3/3 resources)
```

No wildcard source repos or destinations are permitted.

---

## L9.3 — Real Forward GitOps Reconciliation

1. **Change Injected**:
   - P01 (`FlashSale-Backend`): Commit `0ccb6f2` adding proof annotation `proof.local/gitops-marker: forward-1` to deployment `order-api`.
   - P02 (`Productionized-LegacyApp`): Commit `9461c7a` adding proof annotation to deployment `legacy-app`.
2. **Reconciliation Observed**:
   - Argo CD polled upstream GitHub remote.
   - Detected state drift: `Synced` → `OutOfSync`.
   - Reconciled manifests without human CLI intervention.
   - New pods created carrying the forward deployment marker.
   - Final status: `Synced`, `Healthy`.

---

## L9.4 — Real Git Revert Rollback

1. **Rollback Injected**:
   - P01: Commit `308e042` reverting `0ccb6f2` (`Revert "chore(local): gitops forward-deploy proof marker (L9.3)"`).
   - P02: Commit `9c51e4f` reverting `9461c7a` (`Revert "chore(local): gitops forward-deploy proof marker (L9.3)"`).
2. **Reconciliation Observed**:
   - Argo CD observed the Git commit revert on GitHub `main`.
   - Detected drift: `Synced` → `OutOfSync` → `Synced`.
   - Performed rolling update reverting pod annotations back to baseline.
   - Zero downtime maintained during both rollout and rollback.

## GATE

**L9: PASS** — Full GitOps lifecycle proven live against real GitHub repos: automated sync, drift resolution, forward promotion, and clean Git-revert rollback.
