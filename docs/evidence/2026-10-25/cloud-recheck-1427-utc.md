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
