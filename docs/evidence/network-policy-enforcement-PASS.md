# NetworkPolicy Enforcement Verification (Positive & Negative Controls)

## Capable-CNI verification — PASS

- **Execution:** Isolated local cluster `kind-netpol-verification`
- **Node image:** `kindest/node:v1.37.0`
- **CNI:** Calico v3.30.3
- **Scope:** Local enforcement proof only; this does not promote `kind-local-platform` or prove AKS runtime readiness.
- **Control sequence:** The same HTTP probe was run before policy, after a default-deny ingress policy, and after an explicit allow policy.

| Control | Observed result | Verdict |
|---|---:|:---:|
| Before policy | HTTP 200 | **PASS** |
| Default-deny ingress | HTTP 000 / connection blocked | **PASS** |
| Allow policy restored | HTTP 200 | **PASS** |

This causal negative-control proves NetworkPolicy enforcement in a capable-CNI environment. The default `kind-local-platform` cluster still uses kindnet and remains **INCONCLUSIVE** for NetworkPolicy enforcement; AKS production enforcement remains **NOT_VERIFIED** until a live AKS+Cilium observation exists.

> **Correction, 2026-11-03 — enforcement INCONCLUSIVE.** The six probe responses below were observed, but this kind cluster uses the default `kindnet` DaemonSet (`local/kind/cluster.yaml` keeps `disableDefaultCNI: false`). The result does not prove NetworkPolicy caused the denied responses: no policy-toggle control or CNI rule evidence was captured. The mechanism and PASS verdict below are historical claims, not current acceptance evidence. Re-run the same probes on a CNI that implements NetworkPolicy, with an allow/deny policy toggle and captured CNI identity, before closing this gate. See [kind networking configuration](https://kind.sigs.k8s.io/docs/user/configuration/) and [Kubernetes NetworkPolicy prerequisites](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

- **Execution Date:** 2026-10-21T14:57:40Z
- **Environment:** Local Platform (Kubernetes v1.36.1 / kindnet with in-tree nftables CNI engine)
- **Status:** **INCONCLUSIVE for NetworkPolicy enforcement** (six probe observations retained)

## 1. Empirical Results Matrix

| Probe ID | Origin | Target | Type | Expected Behavior | Observed Result | Verdict |
|---|---|---|---|---|---|:---:|
| **NEG-01** | Pod in `default` (unlabelled) | `sre-demo-api:80` | Ingress | Packet dropped / Timeout (RC=28) | Timed out after 3000ms | **PASS** |
| **NEG-02** | Pod in `flashsale` namespace | `sre-demo-api:80` | Ingress | Cross-namespace traffic dropped | Timed out after 3000ms | **PASS** |
| **NEG-03** | Pod in `default` (unlabelled) | `mock-dependency:80` | Ingress | Direct access to leaf blocked | Timed out after 3000ms | **PASS** |
| **NEG-04** | `sre-demo-api` pod | Internet `1.1.1.1:80` | Egress | External egress dropped | `TIMEOUT / ECONNRESET` | **PASS** |
| **POS-01** | `envoy-gateway` pod | `sre-demo-api:80` | Ingress | HTTP 200 allowed by policy | `{"status":"live","uptime_s":3354.248}` | **PASS** |
| **POS-02** | `sre-demo-api` pod | `mock-dependency:80` | Egress | HTTP 200 allowed by policy | `STATUS: 200` | **PASS** |

## 2. Policy Enforcement Mechanism
- The original report attributed the timeouts to kernel-level nftables filtering, but did not capture a CNI implementation or a policy-toggle control that proves this attribution.
- The configured local kindnet setup cannot close the NetworkPolicy enforcement gate; the matrix above records responses, not their cause.
