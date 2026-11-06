# T11b — Azure storage/security inventory lab (read-only)

Scope: Blob/File/Disk, RBAC, encryption, network isolation, Key Vault.
Constraint: read-only / local. No `terraform apply`, no Azure API, no restore actually run. Live resource IDs recorded ONLY when actually deployed — none are.

## Inventory and classification

| Item | Declared in this repo? | Terraform location | Category | Classification | Live? | Validation |
|---|---|---|---|---|---|---|
| Storage account (Blob/File/Disk-capable) | Yes | `terraform/modules/networking/main.tf` (`azurerm_storage_account` "flow_logs", Standard_LRS) | T11b storage | TERRAFORM_ONLY | No | `terraform validate` + `terraform test` |
| Storage account network isolation | Yes | `network_rules { default_action = "Deny"; bypass = ["AzureServices"] }` | T11b network isolation | TERRAFORM_ONLY | No | `terraform test` / `trivy config` |
| Storage retention (flow logs) | Yes | `azurerm_network_watcher_flow_log` `retention_policy { enabled=true; days=... }` | T11b storage | TERRAFORM_ONLY | No | `terraform test` |
| Blob container | No | — | T11b storage | NOT_DECLARED | No | Script asserts absence |
| File share | No | — | T11b storage | NOT_DECLARED | No | Script asserts absence |
| Managed disk | No | — | T11b storage | NOT_DECLARED | No | Script asserts absence |
| RBAC: AKS -> ACR pull (AcrPull) | Yes | `terraform/modules/acr_attachment/main.tf` (`azurerm_role_assignment` "aks_acr_pull") | T11b security | TERRAFORM_ONLY | No | `terraform validate` + `terraform test` |
| AKS RBAC enabled | Yes | `terraform/modules/aks_cluster/main.tf` (`role_based_access_control_enabled = true`) | T11b security | TERRAFORM_ONLY | No | `terraform test` |
| OIDC issuer + workload identity | Yes | `terraform/modules/aks_cluster/main.tf` | T11b security | TERRAFORM_ONLY | No | `terraform test` |
| Key Vault | No | — (only a comment reference in disabled `terraform/legacy/`) | T11b security | NOT_DECLARED | No | Script asserts absence |
| Encryption at rest (storage) | Not explicitly configured | `azurerm_storage_account` has no explicit `encryption` block → platform-managed keys by default | T11b security | NOT_CONFIGURED_EXPLICITLY | No | Gap noted below |

Classification rule: `TERRAFORM_ONLY` = declared in Terraform, never applied to Azure. `NOT_DECLARED` = not present in active Terraform. Nothing is labelled `LIVE`.

## Storage/security gaps (stated, not hidden)

- Storage account encryption is not explicitly configured in `azurerm_storage_account` (platform-managed keys by default); customer-managed keys via Key Vault are NOT_DECLARED because no Key Vault resource exists.
- No pod-level Key Vault secret read has been proven (README: "Key Vault access from a pod ... not a pod performing a secret read against a real vault").
- NetworkPolicy enforcement (`network_policy = "azure"` on AKS) has no observed deny (README: "Cilium-enforced NetworkPolicy ... no policy has been enforced by an observed deny").

## Backup / restore design (fake data — NOT executed)

This is a DESIGN ONLY. No backup or restore was run; no restore log exists and none is claimed.

1. Fake data: write a known dummy object (e.g. `t11b-fake-backup.json` with `{"payload": "synthetic", "seq": 1}`) into a local scratch directory — never into Azure.
2. Simulated backup: copy the scratch file to a timestamped local `backup/` replica; record a SHA-256 digest.
3. Simulated corruption: delete/modify the scratch file.
4. Simulated restore: copy the backup replica back to the scratch path; verify digest matches the recorded digest.
5. Assert: restored digest == original digest.

Expected log line (template, not a captured run):
```
[T11b] backup=sha256:<digest> restored=sha256:<digest> match=true duration_ms=X
```
This log is NOT captured because no restore was executed. It would only be captured after an actual run.

## Verification (this session, local / offline)

- `terraform validate` (5 roots): all valid
- `terraform test` (5 roots): 16 passed, 0 failed
- `trivy config --severity HIGH,CRITICAL ... .`: exit 0 (config scan clean)
- `trivy fs --scanners secret --severity HIGH,CRITICAL ... .`: exit 0 (no secrets)
- `python3 scripts/t11_inventory.py tf-resources`: exit 0; Key Vault / Blob container / File share / Managed disk in NOT_DECLARED

Evidence: commands and exit codes recorded in this session's report.
