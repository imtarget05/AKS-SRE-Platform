# ADR 018: Declarative Edge Routing & Rate-Limiting Contracts

## Status
Accepted

## Context
Previously, `platform/cloudflare/api-edge/src/index.mjs` contained procedural hardcoded routing checks (e.g. checking specific paths like `/flashsale/` + `/api/orders` or `/investigations`) directly within the gateway's core request handler. This created tight coupling between the Cloudflare Edge gateway and application-specific business endpoints: adding or changing an endpoint in FlashSale, OpsBridge, or QuanLyKho required editing the shared platform gateway code.

## Decision
1. **Declarative Route Policy Registry**: Extract route dispatch and rate-limit classification into a declarative registry (`platform/cloudflare/api-edge/src/routes.mjs`).
2. **Stable Traffic Tier Contracts**: Standardize traffic rate-limiting into five platform tiers:
   - `RATE_ORDER` (`order`): High-concurrency flash-sale order submission.
   - `RATE_AUTH` (`auth`): Authentication and token minting endpoints.
   - `RATE_AI` (`ai`): AI investigation and LLM inference endpoints.
   - `RATE_STAFF` (`staff`): Authenticated mutations and administrative actions.
   - `RATE_GENERAL` (`general`): Standard read and informational traffic.
3. **Independent Extensibility**: New applications register their path prefix and declarative policy rules in `ROUTE_REGISTRY` without touching core security, mTLS, CORS, or origin-proof verification mechanisms.

## Consequences
- **Positive**:
  - Reusable Edge Platform: The gateway acts as a product providing standard infrastructure services (mTLS, rate limiting, origin proof, CORS) rather than an application-specific proxy.
  - Testable and declarative: Route policies are validated independently via unit tests (`test/edge.test.mjs`).
  - Zero business logic leakage: Edge does not inspect payload contents or make business decisions.
- **Negative / Trade-offs**:
  - Edge Worker bundles declarative route table configs; route table changes require worker re-deployment.
