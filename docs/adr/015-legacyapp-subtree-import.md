# ADR-015: LegacyApp as an External Workload

## Status

Accepted. LegacyApp is treated as an EXTERNAL workload; the Azure/local source
switch is not performed. The platform holds a GitOps reference only.

## Context

`AKS-SRE-Platform` owns shared Azure/AKS/GitOps resources. `Productionized-LegacyApp`
owns the Node/Express workload, image contract, tests, and Kubernetes manifests.
The committed `Productionized-LegacyApp/main` history was imported (non-squashed)
into `apps/legacy-inventory/` as migration provenance; the original checkout
remains immutable and is not deleted, reset, or pushed by this operation.

The Argo Application `legacyapp` points at the external `Productionized-LegacyApp`
repository (`infrastructure/kubernetes/overlays/prod`), not at this repository.
`gitops/repo-map.yaml` maps `Productionized-LegacyApp` to its external checkout.
`platform/argocd/appproject.yaml` allows `Productionized-LegacyApp.git` as a
sourceRepo for the `portfolio` project.

No Azure resource, cluster, Argo source switch to this repository, registry,
database, or production deployment is performed by this decision. The imported
subtree in `apps/legacy-inventory/` is provenance only and is not the Argo source.

## Decision

LegacyApp is classified `External`:

- Argo Application `legacyapp` (`platform/argocd/applications/legacyapp.yaml`)
  sources from `https://github.com/imtarget05/Productionized-LegacyApp.git`.
- `gitops/repo-map.yaml` maps `Productionized-LegacyApp` to
  `../Productionized-LegacyApp`.
- `platform/argocd/appproject.yaml` `sourceRepos` includes
  `Productionized-LegacyApp.git`.

The local import under `apps/legacy-inventory/` remains for provenance and
offline review; it is not rendered or synced by Argo.

## Rollback

Revert the Argo Application source to the original repository/path in a
reviewed GitOps change, then revert the `gitops/repo-map.yaml` and
`platform/argocd/appproject.yaml` entries. No cluster or Azure mutation occurs.

## Required migration checks

1. `gitops/repo-map.yaml`, `platform/argocd/applications/legacyapp.yaml`, and
   `platform/argocd/appproject.yaml` agree that `legacyapp` is External.
2. Imported `src` tests pass from the subtree; Docker build and Trivy scan pass
   on the imported context.
3. No Azure mutation or Argo source switch to this repository without explicit
   human approval.
