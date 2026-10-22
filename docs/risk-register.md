# Risk Register — AKS-SRE-Platform

Tracked, explicit acceptances of known risks. Each entry records the risk, the controls that
*do* exist, the residual exposure, and an explicit acceptance so nothing stays an
*undocumented exception* in CI.

## RR-01 — Ingress and external-secrets infrastructure are outside the Terraform CI gate

| Field | Value |
|---|---|
| **Status** | **Accepted by repo owner** (2026-10-22; supersedes the earlier undocumented exception) |
| **Likelihood** | Medium |
| **Impact** | Medium (north-south exposure and secret-sync posture would go unvalidated if/when this infrastructure is added) |
| **Residual risk** | Accepted until Phase 7D (shared Gateway API north-south ingress) and any external-secrets adoption land, at which point RR-01 must be replaced by a validation control or re-accepted with a dated rationale. |

### Description

The `terraform` job in `.github/workflows/pr-gate.yaml` validates these roots only:

- `fmt`: `terraform fmt -check -recursive` (whole repo — this part does cover everything)
- `tflint --recursive` from the `terraform/` root
- `terraform test`: `TERRAFORM_TEST_ROOTS` — `terraform/aks-foundation`,
  `terraform/modules/acr_attachment`, `terraform/modules/aks_cluster`

There is **no Terraform resource or module for an ingress controller and no external-secrets
module in this repository** (README, platform-components note; `MANIFEST-INVENTORY.md`).
`kubectl kustomize`-rendered Kubernetes manifests are validated by the *separate*
`kubernetes` job (kubeconform, manifest inventory, policy gate) — not by the Terraform job —
and even there:

1. `kubeconform` **skips** `EnvoyProxy, GatewayClass, HTTPRoute, Gateway` plus the operator
   CRD kinds (`pr-gate.yaml`, kubeconform step) because those kinds have no schema at a fixed
   Kubernetes version. The Argo/KEDA contract is covered by `.github/workflows/gitops-validate.yaml`,
   but **the Envoy/Gateway contract has no equivalent schema or contract check**.
2. A future `ingress-controller`/`external-secrets` Terraform module or manifest set would
   initially land **outside** every CI validation: the `terraform test` guard asserts only the
   roots listed in `TERRAFORM_TEST_ROOTS` (adding a new root to Terraform does not fail CI),
   and schema-validation skip lists mean Gateway-API manifests render unvalidated.

North-south exposure is planned via **Gateway API + Envoy Gateway v1.9.1** (`plans/2026-09-21-master-roadmap-7a-to-13.md`;
`ingress-nginx` is retired upstream and must not be installed). Secret material today comes
only from GitHub secrets / `scripts/bootstrap.sh` inputs, never from in-repo manifests.

### Mitigation currently in place (what DOES validate these surfaces)

- `terraform fmt -check -recursive` covers every `.tf` file in the repo regardless of root.
- `tflint --recursive` lints every `terraform/` subtree with the pinned AzureRM ruleset
  (absolute `--config`, asserted by `tests/test_gates.py` G10).
- Rendered kustomize roots get kubeconform (strict) + manifest inventory (`gitops/validate-gitops.py`)
  + static policy/image gate (`scripts/policy-gate.py`).
- `trivy config` scans IaC **and manifests** repo-wide (HIGH/CRITICAL, exit-code 1).
- Application cluster-int ingress is prevented in the meantime: app Services are `ClusterIP`
  by design (`apps/legacy-inventory/infrastructure/kubernetes/base/service.yaml`), and
  `deploy/base/networkpolicy.yaml` restricts ingress to the shared gateway namespace label —
  so "no ingress controller in the cluster" is the current intended state, not drift.
- `tests/test_gates.py` (CI `python` job) self-asserts the gate is not narrowed back.

### Residual risk

1. A new Terraform root (e.g. `terraform/modules/envoy_gateway`) starts life with zero
   `terraform test` coverage and will not fail CI until someone adds it to `TERRAFORM_TEST_ROOTS`.
2. Gateway/HTTPRoute/EnvoyProxy manifests render unvalidated by Kubernetes CI (schema-skip),
   and uningress exposures introduced by them are caught only by `policy-gate.py` and NetworkPolicy
   review, not schema validation.
3. Secret-sync infrastructure adopted later (external-secrets operator) would have no
   in-repo validation of its CRDs or the `ClusterSecretStore` wiring until RR-01 is revisited.

### Acceptance rationale

Nothing to delete or include in CI exists *today*: there is no ingress module, no
external-secrets manifest, and no workload Route to validate. Gate-scoping them is therefore
a statement about coverage of a future state, and carrying a hard CI control for absent
infrastructure is not possible. The platforms already available (fmt/tflint recursive scope,
trivy config scan, NetworkPolicy default-deny, ClusterIP-only Services) bound the blast
radius while the feature set stays at its present size.

### Exit criteria (closes RR-01)

Any of:

1. Ingress/config-delivery infrastructure is added to the repo → a `terraform test` root and
   a gitops-validate contract test exist for it, `TERRAFORM_TEST_ROOTS` wired, RR-01 closed
   in favour of the real control.
2. The roadmap decision changes (e.g. managed Azure ingress instead of Envoy) → re-assess and
   document the replacement decision in `docs/adr/`.
3. Quarterly re-acceptance: re-verify "no exposition surface exists" (`rg -i "kind: (Gateway|HTTPRoute|Ingress)"`)
   and re-date this entry.
