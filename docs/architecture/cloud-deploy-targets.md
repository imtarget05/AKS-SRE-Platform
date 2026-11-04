# Cloud deployment targets for portfolio web/apps

This repository keeps AKS as an optional infrastructure proof surface, but the live working web and API workloads are designed to land on cloud-native managed edges and runtimes that are reachable from non-VNet laptops.

## Target flow

- Cloudflare Pages / Workers: public web frontends and edge routing.
- Render: application API runtime for the business services.
- Azure: managed control plane, identity, observability, and optional Container Apps / App Service fallback.

## Current repository mapping

| Workload | Primary target | Config | Notes |
| --- | --- | --- | --- |
| `apps/sre-console` | Cloudflare Pages | `apps/sre-console/wrangler.toml` | Static Vite build published from `dist/`. |
| `app/sre-demo-api` | Render | `render.yaml` | Dockerized Node API with health probes and OTEL config. |
| Azure fallback / managed hosting | Azure Developer CLI + App Service | `azure.yaml` | Keeps an Azure-first approval path without blocking local validation. |

## Architectural intent

This flow aligns with a secure, low-friction control-plane model:

1. Public traffic terminates at Cloudflare for TLS, WAF, caching, and edge access control.
2. Business APIs run on Render so they remain simple to deploy and validate outside the private VNet.
3. Azure remains the managed identity, monitoring, and operational approval layer for enterprise workloads.

Production still requires environment-specific secrets, image digests, and owner sign-off. The config files here establish the deployment path, not a live prod acceptance verdict.
