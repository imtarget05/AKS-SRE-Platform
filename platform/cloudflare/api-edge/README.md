# Portfolio API edge — implementation status: CODE VERIFIED, CLOUD NOT DEPLOYED

The Worker exposes fixed prefixes on a `workers.dev` hostname:

| Public prefix | Gateway route owner | Owner path after Gateway rewrite |
| --- | --- | --- |
| `/flashsale/api/...` | FlashSale | `/api/...` |
| `/opsbridge/api/v1/...` | OpsBridge | `/api/v1/...` |
| `/quanlykho/api/v1/...` | QuanLyKho | `/api/v1/...` |

The Worker preserves the prefix for the Azure Gateway. Each workload owns its
HTTPRoute and its API authentication, outlet/branch authorization, idempotency
and database transaction. The Worker cannot select an upstream from request
headers or query parameters. Every API response is `private, no-store`; CDN
cache is reserved for versioned static assets at the individual frontends.

## Local verification

`node --test platform/cloudflare/api-edge/test/*.test.mjs`

The tests cover route allowlists, mTLS and rate binding absence, origin outages,
credential forwarding, request identity header stripping and API cache policy.
They do not prove Cloudflare or AKS runtime.

## Cloud cutover contract

1. Allocate a static Azure public IP and unique Azure DNS label. Install an
   HTTPS Gateway listener with a server certificate for that exact FQDN and a
   ClientTrafficPolicy that trusts only the Cloudflare client certificate CA.
   Verify that a request without the client certificate is rejected at TLS.
   `scripts/render-azure-origin.py` renders the EnvoyProxy, Gateway and
   ClientTrafficPolicy after resource group, public IP, DNS label and Secret
   names are supplied. It never applies them. The existing GatewayClass points
   to that EnvoyProxy; allowed routes require the platform-owned namespace
   label `portfolio.gateway/attach=true`.
2. Upload the Worker client certificate with Wrangler. Copy
   `wrangler.example.toml` to `wrangler.toml` and replace the certificate ID,
   Azure FQDN and allowed static frontend origins. The sample namespace IDs
   must be checked against this Cloudflare account before use. Provision a
   separate random 32-byte-or-longer `EDGE_PROOF_KEY` as a Worker secret and
   keep the matching verification value in the operator's secret store. Never
   put that key in the repository or a command argument.
3. Configure each frontend BFF to call this Worker. For OpsBridge Pages,
   `API_BACKEND_URL` must be
   `https://<edge-worker>.workers.dev/opsbridge`, so
   `/api/v1/...` becomes `/opsbridge/api/v1/...`.
4. Run `python3 scripts/check-cloud-cutover.py`; it currently fails on both
   Applications because they use local overlays, moving `main` refs and
   automated sync. Do not promote until reviewed cloud overlays with managed
   database connections, image digests, secrets, migration and rollback exist.
5. Load `EDGE_PROOF_KEY` from the secret store into the operator environment,
   then run `scripts/test-origin-mtls.sh <origin-fqdn>
   https://<worker>.workers.dev/flashsale/health/live <origin-ca.pem>` only
   after the Gateway and Worker exist. It requires a reachable origin with a
   certificate-required TLS alert, a valid server CA, and a healthy response
   signed with a fresh challenge by this Worker's configured origin binding;
   DNS failure, HTTP `000` alone, or a generic healthy HTTPS page fail. Then prove
   wrong bearer/branch fails at the owner API;
   edge 429 and owner strict limiter are distinct; alert and rollback work.

Cloudflare Workers rate limits are approximate and local to a Cloudflare
location. They protect capacity, not stock, ledger or strict authentication
limits. Runtime and cost claims require exact SHA, image digest, Argo revision,
environment, raw request/DB evidence and actual Azure billing.
