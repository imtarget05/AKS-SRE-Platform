# Azure / Cloudflare recheck — 2026-10-25 14:27 UTC

This recheck records observed state after the OpsBridge API and Cloudflare
Pages rollout. The FlashSale Argo Application source is pinned to the reviewed
OpsBridge merge commit `30320bd53ea85fdfcce6794ac26165c7669f569d` in this
change. The cross-repository GitOps validator fetched that exact commit and
rendered 17 objects; all 35 checks passed. The cloud cutover preflight passed,
and `tests/test_gates.py` passed 52/52 assertions.

| Endpoint / workload | Observed result |
| --- | --- |
| OpsBridge API Deployment | 2/2 Ready on AKS, image built from `3e7fb0d` |
| OpsBridge migration Job | Complete, 1 succeeded, same image as API |
| Edge `/opsbridge/healthz` | HTTP 200 |
| Edge `/opsbridge/health/messaging` | HTTP 200 |
| OpsBridge Pages `/api/v1/auth/me` without token | HTTP 401, no mock user response |
| Edge `/flashsale/health/live` | HTTP 200 |
| Edge `/quanlykho/api/v1/health/live` | HTTP 200 |
| `aks-sre-platform.pages.dev` | HTTP 200 |
| QuanLyKho Cloudflare UI | `Kho Trà Sữa · QuanLyKho`, build `a098d32` |

Argo's live FlashSale Application still has the preceding source pin until
this manifest is applied. Its pre-existing RabbitMQ StatefulSet and completed
`order-migrate` Job differ from the desired source; do not perform a broad
sync without reviewing those two resources. The QuanLyKho Application is also
Healthy but OutOfSync; it still uses internal `bankops-*` Kubernetes names and
database identifiers. The public UI name is QuanLyKho.

## Subsequent reconciliation (14:59 UTC)

- The live FlashSale Application was pinned to `30320bd` and the OpsBridge
  Service, Deployment and HTTPRoute were synced selectively after a successful
  Argo dry run. RabbitMQ's init-container security change was reviewed and
  synced separately; its StatefulSet rolled successfully. FlashSale health and
  OpsBridge messaging health both returned HTTP 200 afterward.
- The live QuanLyKho Application was pinned to `cb53934`. Its API and worker
  were synced to `ghcr.io/imtarget05/bankops-api:sha-df9f7fe` and reached 1/1
  each. A temporary AKS pod-slot shortage was resolved by briefly scaling the
  OpsBridge API from two to one replica; OpsBridge was then restored to 2/2.
  QuanLyKho readiness returned HTTP 200. The remaining dormant resources were
  synced selectively after a successful dry run, leaving Argo **Synced** and
  **Healthy**. Frontend, tunnel and in-cluster Postgres remain at 0 replicas.
- FlashSale is **Healthy** with only the TTL-collected `order-migrate` Job
  reported OutOfSync. The OpsBridge Azure overlay has a tested `PreSync` hook
  change in review to remove that steady-state drift while preserving schema
  ordering for future full syncs.

The migration hook change passed the full OpsBridge PR gate, including stack
smoke and k6, and merged as `b6a2436a31f0378cc3badf3fd81c97c81019e2b2`.
This change updates FlashSale's immutable Argo source pin to that commit.
