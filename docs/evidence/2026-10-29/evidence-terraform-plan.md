# Evidence — Terraform Plan (P3.7)

| Field | Value |
|-------|-------|
| task | P3.7 — Setup docs/evidence/2026-10-29/ (AKS terraform plan) |
| commit SHA | 513df730776939c15895eaa56e77e60b27a823a7 |
| command | `terraform plan` (run against `terraform/aks-foundation`, saved to `/tmp/aks-foundation-plan.tfplan`) |
| output | `Plan: 2 to add, 0 to change, 0 to destroy.` Creates `azurerm_resource_group.aks` (rg-aks-platform-dev, eastasia) and `azurerm_kubernetes_cluster.aks` (aks-portfolio-dev, k8s 1.36, SKU Free, OIDC + workload identity enabled). |
| status | PASS |
| evidence file | `terraform-plan.txt` (symlink → `docs/evidence/live-aks-2026-10-20/terraform-plan.txt`) |

## Summary

- Cluster name: `aks-portfolio-dev`
- Location: `eastasia`
- Kubernetes version: `1.36`
- Node pool: `sys` (1 node, Standard_D2s_v6, autoscaling disabled)
- OIDC issuer: enabled; workload identity: enabled
- Plan saved to: `/tmp/aks-foundation-plan.tfplan`
