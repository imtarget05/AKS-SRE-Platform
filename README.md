# AKS-SRE-Platform — Azure Kubernetes Platform Blueprint (Demo)

Portfolio demo: shared Azure Kubernetes platform (IaC + GitOps + SRE). **Demo only** — no production sign-off.

## Evidence (verified 2026-11-07)

- Release SHA: `0542ac140c36efaf38df8cfa2ec3a4c3d40af261`
- pr-gate: https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42236134325 (success)
- GitOps: https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42236134262 (success)
- SBOM: https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42236134372 (success)
- Azure OIDC: https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42236134355 (success)
- AKS `aks-portfolio-dev`: 4 Ready nodes; ArgoCD app `aks-sre-platform` Synced Healthy at this SHA (2026-11-06 18:30 UTC); KEDA `order-worker-scaler` Ready=True
- Render `sre-demo-api` live on this SHA; Cloudflare Pages https://aks-sre-platform.pages.dev/ serves SRE console build
- Full evidence: see `INTERVIEW_CLOUD_EVIDENCE_2026-11-07.md`

## Open (not claimed)

RabbitMQ `orders` queue created manually (no persistent volume); `order-worker` runs `nginx:alpine` (KEDA healthy != business processing). Cluster cost/owner, recovery drill, production approval remain open. Azure production NO-GO.

## Stack

Terraform, AKS, ArgoCD, KEDA, Prometheus/Grafana, Cloudflare Pages, Render.

## Run locally

See `docs/` and `tasks/current.md`.
