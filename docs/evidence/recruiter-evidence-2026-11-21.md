# Recruiter evidence — AKS-SRE-Platform

Baseline: [`4eaa0ec94cffc4c327145cd98d8031c4bfb8bc23`](https://github.com/imtarget05/AKS-SRE-Platform/commit/4eaa0ec94cffc4c327145cd98d8031c4bfb8bc23), public `main` on 2026-11-21. The commands below ran against a clean clone of this commit on macOS; dependency installation only created ignored local files.

| Verification | Result | Boundary |
| --- | --- | --- |
| `python3 tests/test_gates.py` | 62 passed, 0 failed; G10 passed | Local static regression matrix, not an AKS deployment |
| `python3 scripts/policy-gate.py` | 6 Kustomize roots, 121 objects passed | Maintained local manifests |
| `python3 gitops/validate-gitops.py` | 38 passed, 0 failed, 2 external repos not present | External source trees were not validated |
| `npm ci --prefix app/sre-demo-api` then `npm --prefix app/sre-demo-api test` | 12 passed, 0 failed | Local Node.js demo API |

Public CI at the same SHA: [pr-gate](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/44489443176), [gitops-validate](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/44489443169), [SBOM scan](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/44489443285). These runs succeeded on 2026-11-19. A successful workflow is evidence for its configured jobs, not proof of continuously running production infrastructure.

The [2026-11-19 kind rollback drill](local-kind-rollback-2026-11-19/README.md) is historical evidence, separate from the checks rerun above. Its build digest is recorded, but the restored Deployment records the tag `sre-demo-api:local-drill` and the pod runtime reports an imported kind digest. Thus this drill proves restoration of the original image reference and ready replicas; it does not independently prove that a deploy pipeline promoted the exact build digest. The Azure cluster is not kept running for this portfolio demo.

`aks-deploy.yml` is an infrastructure-only Terraform workflow. Its former `sbom-scan` job referenced the removed `legacy-app` image and was not a dependency of `apply`; this branch removes that stale job. A green Terraform run is not an application image promotion gate. A separate Azure application release path and live AKS/ACR verification are still needed before making that claim.

The [2026-11-21 local digest drill](local-kind-digest-2026-11-21/README.md) supplies that proof for the demo workload on kind. [CI run 44916032886](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/44916032886) passed at `0b873a8`: its fail-closed GitOps validation rendered both external sources before deployment, then the build, registry reference, Deployment, and both ready pod `imageID` values used `sha256:ee364b08713d773f542ad5c167400fcd83e5cb2f738e045f8e030846686b3b2d`. The raw `kind-rollback-evidence` artifact records the digest and rollback. [GitOps validation](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/44916032868) and [PR gates](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/44916033018) also passed on that commit. It remains distinct from Azure application promotion.

The [workload failure triage runbook](../runbooks/workload-failure-triage.md) covers 502, crash loops, OOM, and database timeouts with evidence to collect and rollback criteria. Its database branch applies to external workloads; this repo's demo API has no database.

## Two-minute demo

1. Show the policy gate and G10 result, including the commit SHA.
2. Show the GitOps source gate before deployment and the timestamped digest-pinned kind rollback evidence.
3. Explain the failed deployment, the `ErrImagePull` symptom, the `rollout undo` action, and the limits of local evidence.
