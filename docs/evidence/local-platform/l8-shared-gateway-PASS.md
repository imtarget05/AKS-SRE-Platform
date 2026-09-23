# L8 — Shared Gateway API Routing (Envoy Gateway v1.9.1) — PASS

**Date:** 2026-09-23  
**Cluster:** `kind-local-platform` (Kubernetes v1.36.1)  
**Azure mutated:** NO — local kind only.  

## Architecture

One single shared Gateway (`portfolio-gateway` in namespace `platform-gateway`) routes traffic north-south across both independent project workloads using Kubernetes Gateway API v1:

```text
                  Client (HTTP Request)
                           │
                           ▼
          Envoy Gateway (portfolio-gateway:80)
             Listener: port 80, AllowedRoutes: All
              ┌───────────────────────────┐
              │                           │
Host: flashsale.local              Host: legacy.local
              │                           │
              ▼                           ▼
HTTPRoute: flashsale               HTTPRoute: legacy
(Namespace: flashsale)             (Namespace: legacyapp)
              │                           │
              ▼                           ▼
Service: order-api:80              Service: legacy-app:80
```

## Gateway & Route Resources

1. **GatewayClass**: `portfolio-gatewayclass` (`controller: gateway.envoyproxy.io/gatewayclass-controller`), `Accepted=True`.
2. **Gateway**: `platform-gateway/portfolio-gateway`:
   - `Accepted=True`
   - `Programmed=True`
3. **HTTPRoute `flashsale/flashsale`**:
   - Hostname: `flashsale.local`
   - ParentRef: `platform-gateway/portfolio-gateway`
   - Rule: `/` → `order-api:80`
   - Status: `Accepted=True`, `ResolvedRefs=True`
4. **HTTPRoute `legacyapp/legacy`**:
   - Hostname: `legacy.local`
   - ParentRef: `platform-gateway/portfolio-gateway`
   - Rule: `/` → `legacy-app:80`
   - Status: `Accepted=True`, `ResolvedRefs=True`

## Live Routing Matrix (Measured)

| Request Host | Request Path | HTTP Status | Response Header / Body | Target Pod |
|---|---|---|---|---|
| `flashsale.local` | `/healthz` | **200 OK** | `server: Kestrel`, `{"status":"healthy"}` | `order-api-*` |
| `flashsale.local` | `/api/orders` | **202 Accepted** | `server: Kestrel`, `{"message":"Order accepted"}` | `order-api-*` |
| `legacy.local` | `/health` | **200 OK** | `x-powered-by: Express`, `{"status":"healthy"}` | `legacy-app-*` |
| `unmatched.local` | `/` | **404 Not Found** | (Negative control - no route matches) | Envoy Proxy |

## GATE

**L8: PASS** — Single shared Gateway correctly multiplexes multiple isolated application namespaces with zero cross-tenant interference.
