# `platform/envoy-gateway` — local north-south entry point (L3)

Status: **installed and traffic-proven locally on 2026-09-23** (evidence:
`docs/evidence/local-platform/l3-envoy-gateway-PASS.md`).

This directory owns the **platform-level** north-south path for the local
portfolio cluster. It replaced ingress-nginx, which is retired upstream (see
`tasks/current.md`, Phase 7B.0): north-south is Gateway API + Envoy Gateway, both
locally and on AKS. Application routing (P01/P02) lands on the same Gateway in L8.

| File | Purpose |
|---|---|
| `values.yaml` | Helm values for the pinned chart (CRDs on, capped control-plane memory) |
| `gateway/namespace.yaml` | `platform-gateway` namespace that owns the Gateway |
| `gateway/envoyproxy.yaml` | Data-plane shape: **ClusterIP** service + explicit resources |
| `gateway/gatewayclass.yaml` | `portfolio-gatewayclass` → EG controller, `parametersRef` to the EnvoyProxy |
| `gateway/gateway.yaml` | `portfolio-gateway` (listener `http` :80, same-namespace routes) |
| `gateway/httproute-proof.yaml` | **Temporary** proof route (`/proof`) — kept as a re-runnable harness |
| `proof-backend/` | **Temporary** dependency-free backend (`node:22-alpine`, non-root) |

## Pinned versions (no floating tags)

| Component | Version |
|---|---|
| Envoy Gateway chart | `oci://docker.io/envoyproxy/gateway-helm` **v1.9.1** (digest `sha256:91bae9ae…`) |
| Gateway API CRDs | installed by the chart's `crds` dependency (v1.9.1 pairing) |
| Kubernetes | kind cluster `local-platform`, v1.36.1 |

## Install / verify

```bash
# context guard: this must be the LOCAL cluster
kubectl config current-context          # expect kind-local-platform

helm upgrade --install envoy-gateway oci://docker.io/envoyproxy/gateway-helm \
  --version v1.9.1 --namespace envoy-gateway-system --create-namespace \
  -f platform/envoy-gateway/values.yaml --wait --timeout 5m

kubectl -n envoy-gateway-system get deploy,pods            # envoy-gateway 1/1
kubectl apply -f platform/envoy-gateway/gateway/namespace.yaml \
              -f platform/envoy-gateway/gateway/envoyproxy.yaml \
              -f platform/envoy-gateway/gateway/gatewayclass.yaml \
              -f platform/envoy-gateway/gateway/gateway.yaml
kubectl wait --for=condition=Programmed gateway/portfolio-gateway \
  -n platform-gateway --timeout=180s
```

## Re-run the proof harness (also the L11 demo path)

```bash
# 1. build + load the proof backend (arm64, local, no registry)
docker build --platform linux/arm64 -t flashsale/gateway-proof:local \
  platform/envoy-gateway/proof-backend
local/kind/load-image.sh flashsale/gateway-proof:local

# 2. apply backend + route
kubectl apply -f platform/envoy-gateway/proof-backend/proof-backend.yaml \
              -f platform/envoy-gateway/gateway/httproute-proof.yaml
kubectl -n platform-gateway rollout status deploy/gateway-proof --timeout=120s

# 3. forward and assert
kubectl -n envoy-gateway-system port-forward --address 127.0.0.1 \
  svc/envoy-platform-gateway-portfolio-gateway-d6017b10 18080:80 &
curl -s -i http://127.0.0.1:18080/proof     # expect 200 + LOCAL-ENVOY-GATEWAY-OK
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18080/   # expect 404 (control)
```

**Two traps this README exists to prevent:**

1. `--address 127.0.0.1` is required. Without it `kubectl port-forward` binds
   `[::1]` on this machine and an IPv4 `curl` fails with *"Empty reply"*.
2. Forward to host **18080**, not 8080: host 8080 is already claimed by Docker
   Desktop's mapping for the kind node's reserved `extraPortMapping` (30080).

## Cleanup

```bash
# proof only — keeps the platform
kubectl -n platform-gateway delete -f platform/envoy-gateway/gateway/httproute-proof.yaml \
                                   -f platform/envoy-gateway/proof-backend/proof-backend.yaml

# full removal (destroys the Gateway, data plane and CRDs)
helm uninstall envoy-gateway -n envoy-gateway-system
```

## Known local limitations

- Data plane is `ClusterIP` with **no LoadBalancer**: MetalLB is not installed and
  is not required for the local proof.
- No TLS listener, no rate limiting, no external DNS — none of them is claimed.
- `kindnet` does not enforce NetworkPolicy, so no policy enforcement is claimed.
