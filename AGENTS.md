# Portfolio Engineering Conventions (AGENTS.md)

Guidelines for this monorepo. They apply to **every** project folder here, in every session.

## 1. Stack (current)

- **AKS-SRE-Platform:** Node.js demo API + Terraform + Kubernetes (kind local / Azure AKS) + ArgoCD GitOps + policy-gate.
- Render (`sre-demo-api`) and Cloudflare Pages (`sre-console`) are managed-service mirrors, not infrastructure owned by this repo.
- `.NET / C# / FlashSale Domain/Application/Infrastructure` references are **stale** — removed from this repo. FlashSale-Backend is Java/Spring Boot in its own repo.

## 2. Evidence-first engineering

- Reproduce the problem before fixing it; record real numbers in `docs/benchmarks/` (never fabricate metrics).
- Every significant decision gets an ADR in `docs/adr/`; failures get a postmortem in `docs/incidents/`.
- Keep plans/tasks current (`plans/`, `tasks/`).

## 3. Delivery hygiene

- No secrets in the repo — environment variables / Key Vault / GitHub secrets.
- Containers: multi-stage, non-root, healthcheck, `.dockerignore`.
- IaC must pass `terraform validate`; manifests must render (`kubectl kustomize`).
- Tests must pass locally before claiming completion (`pytest tests/test_gates.py`, `npm test`, container smoke test).
- Terraform state/plan files are **never committed** — remote backend (`azurerm`, storage `stakssre`) only.

## 4. Cloud scope

- Azure AKS and production are **in scope** (decision.local_demo_scope removed).
- `terraform apply` on Azure requires explicit approval before every run (`terraform.no_apply_without_approval_on_destroy`).
- Render Free / Cloudflare Pages are demo-grade managed services; they do not provide customer-owned VPC/VNet.
