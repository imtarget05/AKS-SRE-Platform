# Phase 13 — Service Mesh (Istio ambient)

Manifests for Istio ambient mode (ztunnel mTLS) + AuthorizationPolicy allow/deny matrix.
Envoy Gateway remains north-south; ingress-nginx is NOT installed (retired Mar 2026).

Apply order:
1. Label namespaces for ambient: `istio.io/dataplane-mode: ambient`
2. Apply AuthorizationPolicy resources.
3. Verify mTLS with `istioctl ztunnel-config` and a before/after latency probe.
