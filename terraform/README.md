# Terraform roots

## ACTIVE ROOTS (the only directories you may init/plan/apply from)

| Root | Owns | Backend key |
|---|---|---|
| `terraform/aks-foundation` | Phase 7A AKS cluster foundation (`rg-aks-platform-dev` / `aks-portfolio-dev`, eastasia) | `aks-foundation.terraform.tfstate` |
| `terraform/data-protection` | Pointer note — the real root now lives in `FlashSale-Backend/infrastructure/terraform/backup-storage` | (see its README) |

## HISTORICAL ONLY

| Directory | Content |
|---|---|
| `terraform/legacy` | Superseded Phase 2 draft, kept as `main.tf.disabled` with credentials removed from HEAD. **Never runnable. Never apply.** |

## Rules

1. **DO NOT run terraform from the `terraform/` parent directory.** There is no
   root config here by design; cd into an ACTIVE root only.
2. Raw Terraform plans (`*.tfplan`, `plan.out`, `plan.json`) may contain
   sensitive values — keep them in `.local/` (gitignored), never commit them.
   Committed evidence is the sanitized `docs/evidence/<phase>/` material.
3. `apply` and `destroy` require explicit user approval per phase (Cost Safety
   Mode). The owner-approved 2026-11-05 teardown applied a reviewed plan and
   destroyed four AKS resources; the Terraform state then had no tracked
   resources. No Terraform mutation was run during the 2026-11-06 offline
   validation. The state storage account and other separately scoped Azure
   resources remain. See the [teardown execution record](../docs/runbooks/azure-teardown-runbook.md#10-execution-record--2026-11-05).
