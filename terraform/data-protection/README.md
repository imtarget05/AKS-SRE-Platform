# Data protection moved (Phase 3B)

The backup data-protection Terraform root that used to live here was **moved** to
the application repository so that all backup/restore concerns are versioned next
to the scripts and ADRs that use them:

```text
FlashSale-Backend/infrastructure/terraform/backup-storage/
```

Why the move (and why not into `infrastructure/terraform/main.tf`):

- `infrastructure/terraform/main.tf` is the **application stack** (ACR, Log
  Analytics, PostgreSQL Flexible Server, Redis, Service Bus, Container Apps).
  A `terraform apply` there creates application resources, which Phase 3B
  explicitly forbids ("no AKS / no app deployment in the data-protection phase").
- `backup-storage/` is therefore an **isolated root** that owns only the storage
  account, the private containers, the lifecycle policy, the network rules and
  the RBAC assignment. Terraform state was moved with it, so the already-applied
  resources are still the same resources (no recreate, no drift).
- Repository 03 (`AKS-SRE-Platform/terraform/`) stays the home for cluster-scoped
  infrastructure (AKS, KEDA, ingress) which is out of scope until the AKS phase.

See `docs/adr/008-backup-storage-redundancy.md`,
`docs/adr/009-backup-access-security.md` and
`docs/architecture/backup-data-protection.md`.
