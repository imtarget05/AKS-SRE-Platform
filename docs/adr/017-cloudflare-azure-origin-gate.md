# ADR 017 — Cloudflare API Worker to Azure origin through mTLS

Status: Code and offline gates implemented 2026-10-24; Azure cutover blocked.

## Business problem

Four applications need one understandable request path. Current Argo
Applications point to laptop overlays and moving `main`; a green validator
only proves those local manifests render. A public Azure origin without an
origin authentication boundary would let callers bypass Cloudflare capacity
controls. Returning fake records during an outage would hide operational
failure.

## Decision

Static frontends stay on Cloudflare. One API Worker on `workers.dev` accepts
fixed service prefixes and calls the Azure Gateway through a Cloudflare mTLS
binding. Envoy Gateway terminates HTTPS and validates the Worker client
certificate using ClientTrafficPolicy. Every owner API still validates
JWT/role/outlet/branch; PostgreSQL/MySQL remain the business truth. API
responses use `private, no-store`. Edge rate limiting is approximate capacity
protection; strict login/AI limits belong at the owner service.

The Azure public origin uses a named static IP and an Azure DNS label; the
server certificate must match the resulting `cloudapp.azure.com` FQDN.
`render-azure-origin.py` emits the Envoy resources but never applies them.
`check-cloud-cutover.py` blocks applications that use local/staging overlays,
moving refs or automated first sync. It currently exits 1 for FlashSale and
QuanLyKho as expected.

## Alternatives and trade-offs

Cloudflare Tunnel with a public hostname was deferred because no custom
domain is available. Direct browser calls to Azure were rejected because they
bypass the intended edge. Redis is not used as a global HTTP cache; FlashSale
uses it for stock reservations. The Azure public origin remains internet
routable at TCP level, so the client certificate is the mandatory origin gate.
Certificates, static IP, Azure managed databases, Argo release overlays,
backup/restore, owner strict rate limits and actual cost proof remain release
blockers.

## Verification

The Worker contract tests cover fixed routes, absent mTLS/rate bindings,
origin failure, CORS, credential forwarding and no-store responses.
Renderer unit tests assert HTTPS/443, static IP annotations, route namespace
selector and client CA reference. A cloud claim requires live negative
handshake proof without client cert, authorized end-to-end request, wrong
identity/scope rejection at owner API, exact image digest/Argo revision and
measured cost.
