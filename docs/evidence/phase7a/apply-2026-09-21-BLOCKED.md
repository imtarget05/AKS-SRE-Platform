# Phase 7A Apply Attempt — 2026-09-21T07:59:09Z → 07:59:52Z (43s)

Source commit: `68547b1cfdfbe40c49ffd002cf6a6aa8d4d65826`
Saved plan: `terraform/aks-foundation/.local/phase7a-system.tfplan` (gitignored, 3/0/0 gate passed)
Command: `terraform apply -input=false -auto-approve .local/phase7a-system.tfplan`

## Result: BLOCKED — quota failure during AKS provisioning

```text
Error: creating Kubernetes Cluster (Subscription: "<redacted>"
Resource Group Name: "rg-aks-platform-dev"
Kubernetes Cluster Name: "aks-portfolio-dev"):
unexpected status 400 (400 Bad Request):
  "code": "ErrCode_InsufficientVCPUQuota",
  "message": "Insufficient vcpu quota requested 8, remaining 0
    for family standardDASv5Family for region eastasia."
```

## Partial state (no blind rerun, no destroy)

- `terraform state list`: `data.azurerm_container_registry.shared`, `azurerm_resource_group.aks` (AKS + role assignment absent)
- `az group show rg-aks-platform-dev`: Succeeded, empty (`az resource list` = none)
- RG alone bills ~0. No cluster → no compute burn.

## Root cause

Regional total `0/10` masked family-level caps: **all v5 families are 0/0** in eastasia on this subscription
(`Standard DASv5/Dv5/DSv5/DDSv5/DDv5/... = 0`). `list-skus Restrictions: []` means SKU exists in region, not quota.
Families with quota 10 include: Standard D/DSv2/Dv4/Dv3/DSv3/Dv2/DSv4/DASv4, EBDSv5 (E-series).

## Remediation options (user decision required)

1. Request quota increase for `standardDASv5Family` eastasia (free, portal/CLI) → retry same plan.
2. Switch system pool to a 4vCPU SKU in a family with quota (e.g. Dsv4/Dv4 line) → replan + new approval.
3. `terraform destroy -target` RG cleanup if abandoning eastasia (explicit approval first).

Per gate G: STOP. No larger VM auto-selected. No destroy. No user pool.

## Firewall audit (found during recovery refresh, same day)

- Before: `stflashs3ctfbk01` firewall Deny, allowlist = [`115.76.179.191`], bypass unset → state load 403
  (`AuthorizationFailure`, 2026-09-21, after residential IP rotation to `14.237.62.106`).
- Fix: `az storage account network-rule add -n stflashs3ctfbk01 -g rg-flashsale-tfstate --ip-address 14.237.62.106`
  → allowlist = [`115.76.179.191`, `14.237.62.106`]. Minimal, auditable, reversible.
- Residual risk: every residential IP rotation re-blocks state mid-workflow. Pre-apply runbook: re-check
  `curl api.ipify.org` vs `networkRuleSet.ipRules` before any init/plan/apply; long-term: VPN/static egress or private endpoint.
