# L3 — Envoy Gateway v1.9.1 local north-south proof (PASS)

Date: 2026-09-23 · P03 (`AKS-SRE-Platform`) · **LOCAL ONLY**

> Azure was not created, read for mutation, or changed. This phase ran entirely
> against the local kind cluster `local-platform`.

Baseline commit at phase start: `991ec050f98a93435934f4f7983db6a8b0ba2568`
("feat(local-platform): establish reproducible kind foundation").

## 1. Cluster guard

| Check | Value |
|---|---|
| `kubectl config current-context` | `kind-local-platform` (guard: install aborts on any other context) |
| Kubernetes | v1.36.1 (server + kubectl client) |
| Nodes | 3/3 Ready (1 control-plane + 2 workers), all `linux/arm64` |

## 2. Install (pinned, no floating tags)

| Item | Value |
|---|---|
| Chart | `oci://docker.io/envoyproxy/gateway-helm` **v1.9.1** |
| Chart digest | `sha256:91bae9aedb91ab34731e987afe01a3ccf454393015abeca705eea8ee15553e86` |
| Release / namespace | `envoy-gateway` / `envoy-gateway-system` (rev 1, `deployed`) |
| App version / image | `v1.9.1` / `docker.io/envoyproxy/gateway:v1.9.1` |
| Command | `helm upgrade --install envoy-gateway oci://docker.io/envoyproxy/gateway-helm --version v1.9.1 -n envoy-gateway-system --create-namespace -f platform/envoy-gateway/values.yaml --wait` |
| Controller pod | `envoy-gateway-b4fc6bf9-69rcx` **1/1 Running, 0 restarts** |
| Values override | `crds.enabled=true`; control plane `requests.cpu=100m, requests.memory=128Mi, limits.memory=512Mi` (default limit is 1024Mi — capped for the 7.75 GiB Docker VM) |

Every key in `platform/envoy-gateway/values.yaml` was confirmed with
`helm show values … --version v1.9.1` before use.

## 3. Gateway API + Envoy Gateway CRDs

Installed by the chart's `crds` dependency (`crds.enabled=true`):

- Gateway API: `gatewayclasses`, `gateways`, `httproutes`, `grpcroutes`,
  `tcproutes`, `tlsroutes`, `udproutes`, `referencegrants`,
  `backendtlspolicies`, `listenersets`
- Envoy Gateway: `envoyproxies`, `backendtrafficpolicies`, `clienttrafficpolicies`,
  `envoyextensionpolicies`, `envoypatchpolicies`, `httproutefilters`,
  `securitypolicies`, `backends`

## 4. GatewayClass / Gateway / data plane

| Resource | Evidence |
|---|---|
| `GatewayClass/portfolio-gatewayclass` | `Accepted=True` (reason `Accepted`), controller `gateway.envoyproxy.io/gatewayclass-controller` |
| `Gateway/platform-gateway/portfolio-gateway` | `Accepted=True`, **`Programmed=True`**; listener `http` port 80, `allowedRoutes.namespaces.from=Same` |
| `EnvoyProxy/portfolio-proxy-config` | applied via `parametersRef`; field paths verified with `kubectl explain envoyproxy.spec.provider.kubernetes` on the live CRD |
| Data plane deployment | `envoy-platform-gateway-portfolio-gateway-d6017b10` **1/1** (containers: `envoy` + `shutdown-manager`) |
| Data plane service | type **ClusterIP** (explicit override), port `80 -> 10080` |
| Data plane resources | `envoy` requests `cpu=50m, memory=64Mi`, limits `memory=256Mi` |

Why ClusterIP: kind has no LoadBalancer implementation, so a LoadBalancer Service
would sit `pending` with a meaningless EXTERNAL-IP. ClusterIP + port-forward is
deterministic and needs no MetalLB (deliberately not installed in L3).

## 5. Traffic proof — resources existing was NOT enough

Path actually exercised:

```text
curl (host) -> kubectl port-forward 127.0.0.1:18080
            -> svc/envoy-platform-gateway-portfolio-gateway-d6017b10:80
            -> Envoy listener :10080
            -> HTTPRoute platform-gateway/gateway-proof (PathPrefix /proof)
            -> svc/gateway-proof:80 -> pod:8080
```

| Check | Result |
|---|---|
| `GET /proof` | **`HTTP/1.1 200 OK`**, body: `LOCAL-ENVOY-GATEWAY-OK` + `path=/proof` |
| `GET /` (unmatched — negative control) | **404**, proving the route match is real and not a catch-all |
| `HTTPRoute/gateway-proof` status | `Accepted=True` (reason `Accepted`), `ResolvedRefs=True` (reason `ResolvedRefs`) |
| Envoy access log | `route_name=httproute/platform-gateway/gateway-proof/rule/0/match/0/*`, `upstream_cluster=httproute/platform-gateway/gateway-proof/rule/0`, `upstream_host=10.244.2.4:8080`, `response_code=200`, `response_code_details=via_upstream`, `x-forwarded-for=10.244.1.4`, `x-request-id=614bfaa6-addb-4361-8db0-6d00120dff5b` |
| Backend pod log | `GET /proof peer=10.244.1.4` — the Envoy **pod** IP, so the hop is proven from both ends |

Route status was captured **before** the proof objects were deleted.

### Three gotchas found and fixed (so the L11 demo does not lose time)

1. `kubectl port-forward` binds `[::1]` by default here, so an IPv4 `curl` to
   `127.0.0.1` returned *"Empty reply from server"*. Fix: `--address 127.0.0.1`.
2. **Host port 8080 is already consumed** by Docker Desktop's mapping for the kind
   node's reserved `extraPortMapping` (30080 → host 8080). The proof therefore
   forwards to host **18080**. Consequence: the reserved ports can be used later by
   a NodePort topology, but they are *not* free for ad-hoc forwards.
3. The first proof image crash-looped with
   `exec: "httpd": executable file not found in $PATH`: the local `alpine:latest`
   busybox **has no `httpd` applet** (`busybox --list | grep -x httpd` → empty, and
   no `/bin|/usr/sbin/httpd`). The proof image now uses `node:22-alpine` (already
   present locally, arm64) with the same deterministic body and a non-root user.

## 6. Cleanup (Step 8) — proof only, platform kept

| Deleted | Kept |
|---|---|
| `deployment/gateway-proof`, `service/gateway-proof`, `HTTPRoute/gateway-proof` | Envoy Gateway release (rev 1 `deployed`), Gateway API + EG CRDs, `GatewayClass/portfolio-gatewayclass`, `Gateway/portfolio-gateway`, `EnvoyProxy/portfolio-proxy-config` |

After deletion: `kubectl -n platform-gateway get all` → *No resources found*, and
the Gateway is still `Programmed=True`. No proof pod was left behind (one pod
needed `--force --grace-period=0` after its Deployment was removed).

The proof manifests stay in Git as a **re-runnable harness** (useful for the L11
demo); only the live objects are gone.

## 7. L1 — arm64 application images built from source

| Image | Built from | Architecture | Size (bytes) | Present on nodes |
|---|---|---|---|---|
| `flashsale/order-api:local` | `FlashSale-Backend/Dockerfile` | `arm64/linux` | 103 289 453 | 3/3 |
| `flashsale/order-worker:local` | `FlashSale-Backend/Dockerfile.worker` | `arm64/linux` | 101 153 927 | 3/3 |

Both builds: `docker build --platform linux/arm64 …` → exit 0. Loaded with
`local/kind/load-image.sh`. The ACR-pinned `amd64` images were **not** used, and no
`overlays/prod` image tag was touched. **No P01 source change was required**, so
there is no P01 commit for L1.

Never-pull runtime proof (`imagePullPolicy: Never`):

| Probe | Result |
|---|---|
| `dotnet --info` inside `flashsale/order-api:local` | `Version: 10.0.12`, **`RID: linux-arm64`** → native runtime, no emulation |
| API default entrypoint | container **started**, then fail-closed: `System.InvalidOperationException: Auth:Jwt:SigningKey is required in Production.` (expected — no Secret mounted yet; that is L5) |
| Worker default entrypoint | container **started**, then fail-closed: `MessagingConfigurationException: No messaging provider could be resolved …` (deliberate: no silent InMemory) |
| `exec format error` occurrences | **0** for both images |
| Negative control on the mechanism | a mistyped image ref (`flashsale/order-apiocal`) surfaced `ErrImageNeverPull`, proving pods really consume the locally loaded image instead of pulling |

## 8. Resource measurement (input to the L4 decision)

| Component | Measured (after L3, proof removed) |
|---|---|
| control-plane node | 1.377 GiB |
| worker / worker2 | 388 MiB / 355 MiB |
| **Total of the 7.75 GiB Docker VM** | **≈ 2.12 GiB (≈ 27 %)** |
| Headroom | **≈ 5.6 GiB** |

Envoy Gateway's own slice: controller `req 128Mi / lim 512Mi`; data plane
`req 64Mi / lim 256Mi` (plus `shutdown-manager` `req 32Mi`).

**Conclusion: no Docker memory change is required for L4.** Argo CD non-HA
(≈ 0.7 GiB) fits with a wide margin. The manual bump to 10 GiB becomes worthwhile
before the L5/L10 stack (PostgreSQL + RabbitMQ + Redis + 2 apps + Prometheus +
Grafana) — i.e. **before L5**, not before L4. Raising it remains a manual Docker
Desktop action (§4 of `local/kind/README.md`).

## 9. Gate

| Phase | Result |
|---|---|
| L3 — Envoy Gateway + Gateway API + traffic proof | **PASS** |
| L1 — arm64 images from source + Never-pull proof | **PASS** |
| Azure mutated | **NO** |

## 10. Explicitly not claimed

- No NetworkPolicy enforcement (kindnet), no LoadBalancer IP, no HA — local parity only.
- No TLS listener, no rate limiting, no external DNS: outside L3 scope.
- P01/P02 are not deployed yet (L5/L7). The API/worker exceptions above are the
  expected fail-closed config errors of an app with no Secret/ConfigMap mounted,
  not a defect of this phase or of the images.

