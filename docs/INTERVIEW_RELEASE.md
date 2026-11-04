# AKS-SRE-Platform interview release

## One-sentence pitch

This repository is an Azure platform blueprint that demonstrates Terraform
infrastructure, AKS workload identity, Argo CD GitOps, policy gates, and
evidence-driven SRE validation.

## Five-minute demo

Run from the repository root:

```bash
python3 tests/test_gates.py
python3 scripts/policy-gate.py
python3 gitops/validate-gitops.py
for root in deploy/base deploy/overlays/dev; do
  kubectl kustomize "$root" >/dev/null
done
```

Current local results: **62/62 gate assertions**, policy gate PASS, six
kustomize roots validated in the maintained gate, and GitOps validation with
**38 pass, 0 fail, 2 external-repository-not-present**.

Terraform test roots:

```bash
for root in terraform/aks-foundation \
  terraform/modules/acr_attachment terraform/modules/aks_cluster \
  terraform/modules/networking terraform/modules/observability; do
  terraform -chdir="$root" init -backend=false -input=false
  terraform -chdir="$root" test
done
```

The five roots currently pass **16 tests** in total. Recursive `tflint` also
passes with the repository's pinned AzureRM ruleset.

## Interview talking points

- Terraform owns the Azure boundary; Argo CD owns application reconciliation.
- Workload Identity and managed identity avoid image-pull and application
  secrets where the platform supports them.
- Negative controls are part of the gates: invalid manifests, duplicate
  AppProjects, missing external checkouts, and policy violations must fail.
- Local kind is explicitly a dry-run profile; it is not substituted for Azure
  runtime evidence.

## Honest production boundary

- The repository contains strong offline and historical Azure evidence, but
  current private-link cluster sync/apply requires access from inside the VNet.
- Two external workloads are reported as `NOT_PRESENT` because their source
  checkouts were not supplied to the validator.
- Open decisions remain documented in [tasks/current.md](../tasks/current.md),
  including label drift and the second Argo CD installation.

## Evidence

- [Current tasks and open items](../tasks/current.md)
- [GitOps validator](../gitops/validate-gitops.py)
- [Policy gate](../scripts/policy-gate.py)
- [Azure-first verification ADR](adr/014-azure-first-verification.md)
