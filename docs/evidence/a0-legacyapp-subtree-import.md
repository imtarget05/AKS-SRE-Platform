# A0 — LegacyApp Subtree Import Evidence

**Date:** 2026-10-20
**Platform HEAD after subtree import:** `8c0f66c`
**Source LegacyApp main:** `885d2ec3a2672416404082e3736de80855052928`
**Environment:** LOCAL / offline validation only
**Azure mutation:** NONE

## Merge result

`Productionized-LegacyApp` committed history was imported without squash into:

```text
apps/legacy-inventory/
```

The original checkout remains at `/Users/mainguyenbinhtan/Downloads/Productionized-LegacyApp` with its working tree preserved. Its uncommitted observability diff was applied to the imported subtree after the history import; no source reset or deletion occurred.

## Ownership change prepared

The maintained Application is now prepared to use:

```text
repoURL: https://github.com/imtarget05/AKS-SRE-Platform.git
path: apps/legacy-inventory/infrastructure/kubernetes/overlays/prod
namespace: legacyapp
```

The AppProject allowlist includes the platform repository. The old `gitops/applications/legacyapp.yaml` remains as disabled migration provenance and is excluded from the maintained validator. No cluster has been synced and no Argo source switch was applied.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| Imported LegacyApp tests | PASS, 4/4 | `cd apps/legacy-inventory/src && npm test` |
| Production npm audit | PASS, 0 vulnerabilities | `npm audit --omit=dev` |
| Production Kustomize render | PASS, 2 objects | `kubectl kustomize apps/legacy-inventory/infrastructure/kubernetes/overlays/prod` |
| Legacy manifest gate | PASS | `bash apps/legacy-inventory/scripts/validate-manifests.sh` |
| Manifest negative controls | PASS, 9/9 mutations caught | `python3 apps/legacy-inventory/scripts/test-validate-manifests.py` |
| Docker image build | PASS | `docker build -f apps/legacy-inventory/Dockerfile -t legacy-app:subtree-gate apps/legacy-inventory` |
| Trivy image | PASS, 0 HIGH/CRITICAL | `trivy image --severity HIGH,CRITICAL --exit-code 1 --ignore-unfixed legacy-app:subtree-gate` |
| GitOps ownership/source validator | PASS, 18/18 with local maps | `gitops/validate-gitops.py --repo-map ... --require-external` |

## Remaining approval boundary

The source switch is prepared but not deployed. A human must review the rendered Argo Application diff and approve the first GitOps sync against a real cluster. Until then, the standalone LegacyApp repository remains the operational rollback/provenance reference.