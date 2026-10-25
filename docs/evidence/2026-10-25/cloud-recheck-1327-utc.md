# Cloud recheck — 2026-10-25 13:27 UTC

This is a point-in-time read of Azure AKS and the Cloudflare edge. It does not
replace the earlier G0–G7 acceptance record, which describes an earlier commit
and sync. No Docker-based verification or cluster mutation was performed in
this recheck.

## Source and release gates

| Repository | Local HEAD | Latest checked remote gate |
| --- | --- | --- |
| OpsBridge | `3e7fb0d30dd2a5caffd3a7b9c73ec24367e11bf0` | [CI](https://github.com/imtarget05/OpsBridge/actions/runs/40185916621) and [k6](https://github.com/imtarget05/OpsBridge/actions/runs/40185916691) succeeded on this SHA |
| QuanLyKho | `cb5393410d7a75a4e7b8d47534db6fb38b5bad36` | [CI](https://github.com/imtarget05/QuanLyKho/actions/runs/40182564016) and [S10](https://github.com/imtarget05/QuanLyKho/actions/runs/40182563903) succeeded on this SHA |
| AKS-SRE-Platform | `204d82077c85b93d9f1df09389243998910c59a3` | [PR gate](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/40191319105) and [GitOps validation](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/40191319108) succeeded on this SHA |

The platform working tree now proposes changing the FlashSale Application's
source to `OpsBridge@3e7fb0d` and its AppProject allowlist accordingly. The
cross-repository validator rendered exact remote revisions for all three
Applications: **35 pass, 0 fail**. These local edits have **not** been applied
to AKS or pushed as a platform release.

## Live AKS state

`az account show` selected subscription `a3deec78-7edb-41cd-9e94-ec1d4d9379f5`.
All reads pinned `kubectl --context aks-portfolio-dev`. Both nodes reported
`Ready`.

| Argo Application | Live source revision | Sync | Health | Out-of-sync resources |
| --- | --- | --- | --- | ---: |
| flashsale | `FlashSale-Backend@4a19aeb0a25bfc874c46cad73741b3e5e6a8892e` | OutOfSync | Healthy | 1 migration hook Job |
| quanlykho | `QuanLyKho@df9f7fed1998a7999d8353a500c1000c9de27637` | OutOfSync | Healthy | 11 resources |

The platform checkout currently pins `QuanLyKho@cb53934`, so applying the
platform Application as-is would change the live source revision. Inspect the
drift before any sync. A plain `kubectl diff -k` cannot produce a complete
diff here because the already completed migration Job has an immutable pod
template; Argo's PreSync hook lifecycle must be considered separately.

FlashSale's order API (2/2), worker (1/1), and payment service (1/1) were
available. QuanLyKho's API and worker were each 1/1. The namespace has no
OpsBridge API/Web Deployment or Service; its manifests exist in the OpsBridge
repository but are not part of the Azure overlay or published as cloud images.

## Public edge probes

| Request through `portfolio-api-edge.tanmainguyenbinh.workers.dev` | Result |
| --- | --- |
| `GET /flashsale/health/live` | 200, `{"status":"healthy"}` |
| `GET /quanlykho/api/v1/health/live` | 200, `{"status":"alive",...}` |
| `GET /flashsale/api/products/1` | 200, product ID 1 and available stock 2 |
| `GET /opsbridge/healthz` | 404; OpsBridge is not a live public API yet |

These are health/read probes only. They do not prove a new order, maker–checker
journey, migration, rollback, or the still-undelivered OpsBridge API/Web.
