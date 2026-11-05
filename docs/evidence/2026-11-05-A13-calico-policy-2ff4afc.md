# A13 — maintained NetworkPolicy enforcement on capable local CNI

**Verdict:** PASS for A13 local enforcement on source SHA `2ff4afc6be302cb01fc542bb252fdf83ec3869a6`. This is not Azure AKS evidence and does not close A16.

- UTC window: 2026-11-05 06:40:41–06:42:26; teardown completed afterward.
- Environment: isolated `kind-portfolio-a13-main`, Kubernetes `v1.36.1`, Calico `v3.33.0`. Original `kind-local-platform` context was restored.
- Source: `git show 2ff4afc6be302cb01fc542bb252fdf83ec3869a6:deploy/base/networkpolicy.yaml`, applied without edits in namespace `a13-verification`.
- Maintained policy SHA-256: `f3e04e46477b2147d117f93b89d1096a015acc299f595fea8bfd4fde17bf0296`.
- Calico node image: `quay.io/calico/node@sha256:565d8db3200e443955557f8f28ff44ab8a4a456754bc74a19c4f2f3444af9b1c`.
- Full UTC log, policy YAML, pod IPs, exit codes and teardown: [raw probe log](2026-11-05-A13-calico-policy-2ff4afc.log), SHA-256 `915c74b54a524f3be36d7ccdb6ed4bf3327fcf1b4e4739ad631494b15fe55166`.
- Same-SHA [pr-gate](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41981996192), [GitOps](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41981996268), [SBOM](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41981996184) and [OIDC read-only workflow](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41981996292) all completed successfully.

## Method and observed result

The probe created a fresh kind cluster with `disableDefaultCNI: true` and installed the pinned Calico manifest. It ran HTTP from an unauthorized client pod to the same API pod IP before and after applying the maintained policy. It then tested an allowed gateway pod (namespace and pod labels matching the policy), an unauthorized client to the mock dependency, and allowed API-to-mock traffic. The API and mock were local Python HTTP servers on TCP/8080; this tests policy behavior without claiming the real workloads ran.

| Stage | Expected | Actual |
| --- | --- | --- |
| Unauthorized client → API before policy | HTTP 200 | HTTP 200, exit 0 |
| Same client → same API after policy | Blocked | curl timeout, HTTP 000, exit 28 |
| Labeled gateway → API after policy | HTTP 200 | HTTP 200, exit 0 |
| Unauthorized client → mock after policy | Blocked | curl timeout, HTTP 000, exit 28 |
| API → mock after policy | HTTP 200 | HTTP 200, exit 0 |

The script deleted `portfolio-a13-main` after the probe; only the preexisting `local-platform` kind cluster remained. The Azure private cluster, its workload placement, NetworkPolicy enforcement there, Terraform state, cost and rollback still require A16 evidence.

With A13 counted, the strict snapshot becomes AKS **13/14 = 92.86%**, QuanLyKho **0/21**, CreditFlow **0/22**, portfolio **30.95%**. This remains below the >90% target and is separate from production go-live.
