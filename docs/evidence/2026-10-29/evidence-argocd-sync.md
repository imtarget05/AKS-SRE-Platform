# Evidence — Argo CD Sync (P3.7)

| Field | Value |
|-------|-------|
| task | P3.7 — Setup docs/evidence/2026-10-29/ (AKS Argo CD sync evidence) |
| commit SHA | 513df730776939c15895eaa56e77e60b27a823a7 |
| command | `kubectl get applications -n argocd` + `kubectl get pods -n argocd` |
| output | 7/7 Argo CD components Running, 0 restarts; Applications `flashsale` and `legacyapp` Synced/Healthy; all services ClusterIP-only; no floating tag (pin v3.5.5 in `platform/argocd/VERSION`). |
| status | PASS |
| evidence file | `argocd-l4-PASS.md` (symlink → `docs/evidence/local-platform/l4-argocd-PASS.md`), `selfheal-application-syncpolicy.txt` (symlink → `docs/evidence/local-platform/2026-10-21-recreate/selfheal-application-syncpolicy.txt`) |

## Summary

- Install: official version-pinned `manifests/install.yaml`, server-side apply, non-HA mode, namespace `argocd`
- Version pin: v3.5.5 (`platform/argocd/VERSION`, single source of truth)
- Health: 7/7 components Running, 0 restarts
- Exposure: ClusterIP only, no LoadBalancer/NodePort; Argo UI via `kubectl port-forward`
- Sync policy: selfHeal + automated sync evidenced in `selfheal-application-syncpolicy.txt`
