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
3. `apply` requires explicit user approval per phase (Cost Safety Mode).
   Approved scope so far: **nothing has been applied successfully yet** — see
   `../tasks/current.md`.
