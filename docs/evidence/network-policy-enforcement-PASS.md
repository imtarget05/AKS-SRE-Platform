# NetworkPolicy Enforcement Verification (Positive & Negative Controls)

- **Execution Date:** 2026-10-21T14:57:40Z
- **Environment:** Local Platform (Kubernetes v1.36.1 / kindnet with in-tree nftables CNI engine)
- **Status:** **PASS** (Zero unauthorized ingress/egress leakage)

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
- NetworkPolicy is enforced via kernel-level nftables filtering by the CNI engine.
- Default deny rules (`default-deny`) unconditionally drop unapproved ingress and egress packets.
- Only pods carrying explicit matching selector labels in allowlisted namespaces are permitted to traverse ingress/egress ports.
