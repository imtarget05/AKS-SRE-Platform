# L4 — Argo CD Local Non-HA — PASS

**Date:** 2026-09-23
**Cluster:** `kind-local-platform` (Kubernetes v1.36.1)
**Azure mutated:** NO — local kind only.

## Version / Mode

| Item | Value |
|---|---|
| Argo CD | **v3.5.3** (`quay.io/argoproj/argocd:v3.5.3`) |
| Install method | official version-pinned `manifests/install.yaml`, server-side apply |
| Mode | **non-HA** multi-tenant bundle (LOCAL / PORTFOLIO / DEMO — not HA) |
| Namespace | `argocd` |

No floating tag (`stable`/`latest`/`main`) was used.

## Health — 7/7 components Running, 0 restarts

```
argocd-application-controller-0                     1/1  Running  0  165m
argocd-applicationset-controller-84549767db-fsh2k   1/1  Running  0  165m
argocd-dex-server-6cc5dd7c9d-fr42l                  1/1  Running  0  165m
argocd-notifications-controller-57d4c66f69-n2nmd    1/1  Running  0  165m
argocd-redis-c55679569-7wt8j                        1/1  Running  0  165m
argocd-repo-server-7f9fdfbb74-rw5lk                 1/1  Running  0  165m
argocd-server-5f785dd555-bxl4h                      1/1  Running  0  165m
```

Components verified present: application-controller (StatefulSet), repo-server,
server, redis, dex, applicationset-controller, notifications-controller.

## Exposure — private only

```
argocd-server   ClusterIP   <none>   80/TCP,443/TCP
argocd-redis    ClusterIP   <none>   6379/TCP
argocd-repo-server ClusterIP <none>  8081/TCP,8084/TCP
```

- **All Argo services are ClusterIP.** No LoadBalancer, no NodePort.
- Admin/UI access path: `kubectl -n argocd port-forward --address 127.0.0.1 svc/argocd-server ...`
- Argo UI is deliberately **not** routed through Envoy Gateway.

## Resource budget after install (L4.1)

Measured with `docker stats` on the 7.75 GiB Docker VM:

| Container | Memory |
|---|---|
| local-platform-control-plane | 1.584 GiB |
| local-platform-worker | 1.256 GiB |
| local-platform-worker2 | 973.9 MiB |
| **kind total (Argo + Envoy + FlashSale)** | **≈ 3.81 GiB / 7.75 GiB** |

No OOM, no eviction, no restart attributable to memory. Headroom ≈ 3.9 GiB.
**No Docker memory change was required for L4** (measured, not assumed).
The 10 GiB recommendation remains only as a pre-L5/L10 lever if pressure appears.

## Version pin rationale

Argo CD non-HA is upstream's evaluation/demo/testing topology; the full
multi-tenant bundle (API server + UI present) is what was installed. The
pinned v3.5.3 manifest — not `stable` — keeps the local control plane
reproducible.

## Not claimed

- NOT HA (single replica per component by design).
- No AppProject/Application objects yet — created in **L9**.
- No admin UI exposure outside `kubectl port-forward`.

## GATE

**L4: PASS** — pinned install, 7/7 healthy, ClusterIP-only, budget measured.
