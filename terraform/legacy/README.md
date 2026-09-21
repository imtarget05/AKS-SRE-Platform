# terraform/legacy — HISTORICAL ONLY

Everything in this directory is a **superseded blueprint draft** kept for
portfolio history. Nothing here reflects approved or applied infrastructure.

**DO NOT `terraform init`, `plan`, or `apply` from this directory.**

## Why the draft was superseded

`main.tf.disabled` (renamed so no tooling treats it as a runnable root) is the
original Phase 2 draft. ADR-012 v2 rejected its approach:

| Draft (`main.tf.disabled`) | Current direction (`../aks-foundation`) |
|---|---|
| `rg-aks-platform-prod` / `aks-platform-prod` | `rg-aks-platform-dev` / `aks-portfolio-dev` (portfolio, not prod) |
| `southeastasia` | `eastasia` (SE-Asia D-SKUs are subscription-blocked — live quota evidence) |
| `Standard_D2s_v3` system pool | `Standard_D4as_v5` (AKS system-pool minimum ≥4 vCPU/node) |
| Autoscaling 1–5 | Fixed count 2, autoscaler OFF (cost safety) |
| Terraform-managed Helm RabbitMQ + Kafka | Apps deploy via Argo CD/GitOps; middleware via PaaS later |
| Hardcoded Helm credential | Removed from HEAD 2026-09-21; secret references only (External Secrets / Key Vault) |
| Container Insights + Log Analytics by default | Not provisioned during the proof phase (cost rule) |
| Local state | azurerm remote backend, dedicated state key |

The secret hygiene rewrite is documented in `tasks/current.md` Notes; original
history remains in the Git log for this file's previous paths.
