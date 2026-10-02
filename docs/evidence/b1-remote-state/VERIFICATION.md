# AKS-SRE — remote Terraform state foundation (B1)

```text
verified_at : 2026-10-02
method      : read-only Azure API/CLI reads + a real `terraform init`
mutations   : state resource group, one storage account, one container,
              one Blob Data Contributor role for the operator
status      : REMOTE_BACKEND = VERIFIED_LIVE
```

## What was actually wrong

The backend block was not missing — it was **wrong**. It carried hardcoded
values pointing at another repository's state store:

```hcl
resource_group_name  = "rg-flashsale-tfstate"
storage_account_name = "stflashs3ctfbk01"   # belongs to FlashSale-Backend
```

That storage account does not exist in this subscription, so `terraform init`
failed with `dial tcp: lookup stflashs3ctfbk01.blob.core.windows.net: no such
host`. The failure was at least **fail-closed** — it did not fall back to local
state — but the root was un-initialisable and therefore un-deployable.

This is why the audit rule was *copy MAIA's pattern, never MAIA's resources*:
the coupling here was a leftover pointing at a neighbouring repo, and it
presented as a quota or network fault rather than as a configuration error.

## What exists now

| Field | Value |
|---|---|
| State resource group | `rg-aks-tfstate` (southeastasia, tags project=aks-sre) |
| Storage account | `stakssre` (Standard_LRS, StorageV2, TLS1_2) |
| HTTPS only | `true` |
| Anonymous blob access | `false` |
| Shared key access | **disabled** (`allowSharedKeyAccess` = null, Azure's disabled default) |
| Container | `tfstate`, reachable via `--auth-mode login` with no account key |
| State key | `aks-sre/validation.terraform.tfstate` |
| Operator Blob role | `Storage Blob Data Contributor` **@ storage account scope** |
| Local authoritative state | **none** — `ls *.tfstate` is empty |

## Proof, not assertion

```text
terraform init -reconfigure -backend-config=environments/validation/backend.hcl
  -> Successfully configured the backend "azurerm"

## Controls that keep this from regressing

`terraform/aks-foundation/tests/probe_backend_isolation.py` — rules S1–S8, each
with a negative control:

| Rule | What it prevents |
|---|---|
| S1 | a client secret appearing in the backend path |
| S2 | a storage account key or SAS appearing in any backend config |
| S3 | an environment that does not require Entra auth |
| S4 | two environments sharing one state key |
| S5 | **this repo naming another project's state resources** — including MAIA's and the original `stflashs3ctfbk01` |
| S7 | `use_oidc` hardcoded into committed config, which forces the GitHub-only OIDC path and breaks a local `az login` init |
| S8 | **a missing backend config silently falling back to local state** |

S8 is proven by **running** `terraform init` in a throwaway copy with the
backend config removed and requiring a non-zero exit. It is not a grep: the
failure mode it prevents is silent, and every other rule would stay green while
it happened.

Verified by mutation against the real repository:

```text
backend.hcl -> sttfmaia   (MAIA's storage)
  -> FAIL S5 ... references 'sttfmaia', which belongs to another project
backend.hcl + use_oidc = true
  -> FAIL S7 ... forces the GitHub-only OIDC path and breaks a local az login init
```

## Network posture — a documented trade-off

Public network access is **ENABLED** on this account, and that is deliberate:

```text
PUBLIC_NETWORK_REACHABLE + ENTRA_AUTH_REQUIRED + SHARED_KEY_DISABLED
```

A GitHub-hosted runner has no stable outbound IP, so an allow-list would break
CI. The control that matters is that SharedKey authorisation is refused
server-side, so there is no account key to leak in the first place. A private
endpoint with an Azure-hosted runner is the hardened option if this ever needs
locking down; it is not private-endpoint-protected today and this document does
not claim otherwise.

## Cost

This storage account **can incur small ongoing cost** (capacity + transactions).
It is **not** a compute-quota consumer and does not touch the 10-vCPU regional
ceiling. It is permanent by design: transient application teardown must never
destroy it.

## CI OIDC

```text
CI_OIDC = NOT_CONFIGURED
```

This repository has no GitHub OIDC identity of its own. B1 covered state
foundation only; creating a repo-owned identity is a separate authorisation. The
backend is already OIDC-compatible, so adding one later requires no config
change — only `ARM_USE_OIDC` / `ARM_USE_AZUREAD_AUTH` and the three identifiers.

## Bootstrap

```bash
./scripts/bootstrap_state.sh --dry-run          # intent, zero mutation
ALLOW_AZURE_MUTATION=1 ./scripts/bootstrap_state.sh
```

Idempotent: a re-run reads back and reports "already exists" rather than
failing. Two behaviours were added after they were hit in practice:

- **Global name preflight.** Storage account names are unique across *all* of
  Azure. The first attempt (`staksstate`) failed with
  `StorageAccountAlreadyTaken` **after** the resource group was created, leaving
  a half-built foundation. The check now runs first and refuses with exit 4.
- **`allowSharedKeyAccess` accepts `null`.** Azure returns `null`, not `false`,
  when SharedKey is disabled. Asserting on the literal string `False` reported
  a failure for a correctly configured account — a control that cries wolf gets
  switched off.

## Not done here

No `terraform apply` was run. `enable_workload_pool` defaults to `false`, and the
node sizing problem recorded in the portfolio audit (2 × D4s_v6 + 1 × D2s_v6 =
10 vCPU against a 10 vCPU ceiling, leaving no autoscaling headroom) is **not**
addressed by this change. B1 did not alter node sizing, as intended.
terraform validate            -> Success!
terraform plan (read-only)    -> Plan: 2 to add, 0 to change, 0 to destroy

state blob via Blob API (Entra auth):
  aks-sre/validation.terraform.tfstate
```

`PROD_STATE = TARGET_ONLY / NOT_CREATED`. Only `validation` was created. No prod
state was generated merely because the target architecture mentions production.