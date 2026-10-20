# ADR-015: History-Preserving LegacyApp Subtree Import

## Status

Accepted for local migration preparation. Azure source switch is not approved or performed.

## Context

`AKS-SRE-Platform` owns shared Azure/AKS/GitOps resources. `Productionized-LegacyApp` owns the Node/Express workload, image contract, tests, and Kubernetes manifests. The current Argo Application points directly to the LegacyApp repository. The target interview solution needs one platform repository view while preserving release provenance and owner boundaries.

Both repositories have different histories and the LegacyApp checkout contains uncommitted observability work. The original checkout must remain available until the source switch, rollback, and CI gates are accepted.

## Decision

Import the committed `Productionized-LegacyApp/main` history into:

```text
apps/legacy-inventory/
```

using a non-squashed `git subtree` import. The imported application remains an application-owned subtree; platform files outside that path remain platform-owned. The source repository remains immutable migration provenance and is not deleted, reset, or pushed by this operation.

The maintained Argo Application under `platform/argocd/applications/legacyapp.yaml` will be changed only after the imported tree renders and its local application gates pass. Its source will then point to this repository and `apps/legacy-inventory/infrastructure/kubernetes/overlays/prod`. The old `gitops/applications/legacyapp.yaml` is historical/legacy and is not a second live Application source.

No Azure resource, cluster, Argo instance, registry, database, or production deployment is changed by this local import.

## Rollback

Before source-switch approval, rollback is `git revert` of the subtree import and any local source-path commit, while retaining the original `Productionized-LegacyApp` repository. After source-switch approval, rollback means reverting the Argo Application source to the original repository/path in a reviewed GitOps change, then reverting the imported subtree only after runtime stability is accepted.

## Required migration checks

1. `git subtree` history contains the LegacyApp commits and the target path is complete.
2. Imported `src` tests pass from the subtree; Docker build and Trivy scan pass on the imported context.
3. Imported production Kustomize overlay renders and points to an immutable image tag/digest.
4. Maintained Argo Applications have unique names/namespaces/object ownership and the AppProject allows the new repository source.
5. The source checkout's uncommitted observability diff is preserved separately and is applied only after the committed import is verified.
6. No Azure mutation or Argo source switch occurs without explicit human approval.