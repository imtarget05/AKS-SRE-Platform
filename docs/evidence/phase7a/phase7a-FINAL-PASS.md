# Phase 7A FINAL — PASS (2026-09-21)

7A.1 foundation PASS (`docs/evidence/phase7a/system-foundation-PASS.md`,
freeze commit `e66cd0c`) + 7A.2 proofs below. Cluster `aks-portfolio-dev`
(eastasia, 1.36.4, Free tier) ran 16:16:59Z → stop 16:35:45Z (≈19 min), final
state **`powerState=Stopped`, `provisioningState=Succeeded`**.

## Gate results (all runtime-executed, none config-inferred)

1. System foundation healthy ✅ (2/2 sys Ready pre- and post-proofs)
2. Temp D2s_v6 user pool created ✅ (`work`, User, Regular, 1 node, Succeeded)
3. Workload on user pool ✅ (placement + ACR + WI pods all on `aks-work-…`)
4. Nothing on system pool ✅
5. SHA image pulled ✅ (`legacy-app:2d5d07…`, digest `671bbc4e…` match)
6. No imagePullSecret ✅ (spec empty)
7. Kubelet identity + AcrPull ✅ (stated as NOT WI)
8. WI ServiceAccount ✅ (`wi-proof`, client-id annotation, no secrets in YAML)
9. Pod label `azure.workload.identity/use: "true"` ✅
10. FIC issuer/subject/audience match ✅ (issuer compared live)
11. Federated token exchange ✅ (`az login` exit 0)
12. Harmless read ✅ (`az acr show` → Standard, admin false)
13. No secret/key/certificate ✅
14. Namespace deleted ✅ (`phase7a-proof` NotFound verified)
15. UAMI/FIC/Reader deleted ✅ (UAMI `ResourceNotFound` verified; AcrPull intact)
16. User pool deleted ✅ (only `sys` remains)
17. Quota ≈8/10 ✅ (regional 8/10, Dsv6 8/10 after cleanup, pre-stop)
18. Cluster stopped ✅
19. Evidence sanitized ✅ (IDs truncated/withheld, no tokens/tokens-files in repo)

## Quota timeline

Stopped (pre-start): 0/10 → Running sys-only: 8/10 → proof window: ~10/10
(zero headroom; no unrelated ops performed) → after pool deletion: 8/10.

## Cost

- Running window ≈0.32h × $0.554 (2×D4s_v6) ≈ **$0.18**
- Work pool ≈0.16h × $0.139 (1×D2s_v6) ≈ **$0.02**
- Estimated proof compute ≈ **$0.20**. NOT zero total: disks + public IP +
  Standard LB persist while stopped (small, ongoing).

## Failures encountered (all recovered, all evidence)

- `mcr.microsoft.com/oss/nginx/nginx:1.9.3` → NotFound (bad tag) → placement
  proof redone with `registry.k8s.io/pause:3.10`.
- `wi-proof.tf` schema: `parent_id` rejected by azurerm 5.6.0 →
  `user_assigned_identity_id`; `fmt` realigned. `validate` Success before planning.
- Known provider-block null normalizations appeared in plans (cluster + pool
  in-place, no replace/destroy) — accepted as documented 7A.1 debt; sys nodes
  stayed Ready throughout.

## Things we can now truthfully claim

Live AKS 1.36.4 operated (start→verify→stop) · user-pool isolation proven at
runtime · private ACR pull via kubelet+AcrPull with digest match and no secret ·
Entra Workload Identity token exchange + scoped Reader read with no secret ·
full cleanup (quota + stopped state) · exact compute spend ≈$0.20.

## Things we still cannot claim

- no ingress-nginx
- no Argo CD
- no P01 permanently deployed on AKS
- no P02 permanently deployed on AKS
- no Prometheus/Grafana yet
- no microservices/Kafka/Saga yet

## PHASE 7A FINAL GATE

**PASS**

## NEXT (not implemented — STOP)

PHASE 7B — PLATFORM BOOTSTRAP: persistent user workload pool +
shared ingress-nginx + Argo CD + namespace/GitOps foundation.
