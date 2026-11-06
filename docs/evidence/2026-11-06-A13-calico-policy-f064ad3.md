# A13 local NetworkPolicy causal probe — 2026-11-06 UTC

**Verdict:** PASS for the isolated local kind + Calico test only. This does not prove Azure AKS policy enforcement or A16.

- Source SHA tested: `f064ad352a3e7748cacf41a67a21fa513b2624b8`.
- Environment: isolated local kind `w1-a13-main`, Kubernetes v1.36.1, Calico v3.33.0; default CNI disabled and pod subnet `192.168.0.0/16`.
- Calico image: `quay.io/calico/node@sha256:565d8db3200e443955557f8f28ff44ab8a4a456754bc74a19c4f2f3444af9b1c`.
- Probe images: nginx and curl images pinned by digest; pod IPs and all image IDs are in the [raw probe log](2026-11-06-A13-calico-policy-f064ad3.txt).
- The pinned Calico manifest was installed from `https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/calico.yaml`.

The same curl command was run from `a13-client` against the same `a13-target` pod IP for all stages. The test applied an ingress policy selecting `app=a13-target`, first with no allowed ingress and then allowing TCP/80 only from `app=a13-client`. Six seconds were allowed after each policy change.

| Stage | Expected | Actual |
| --- | --- | --- |
| Before policy | HTTP 200 | HTTP 200, exit 0 |
| Default deny | Connection blocked | HTTP 000 timeout, exit 28 |
| Explicit allow | HTTP 200 | HTTP 200, exit 0 |

The temporary kind cluster was deleted after collecting the evidence; no other kind clusters existed at teardown. **A13 is LOCAL only — not Azure.**
