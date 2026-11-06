# Offline validation and Azure inventory — 2026-11-06

- **Captured:** 2026-11-06 03:28 UTC
- **Repository:** `imtarget05/AKS-SRE-Platform`
- **Base SHA checked:** `3fac87e1ad867940946a36e04d3afb3ffe71722e`
- **Branch:** `docs/offline-validation-2026-11-06`
- **Safety:** read-only Azure inventory; no Terraform apply/destroy, cluster creation, Azure resource creation, or real secrets used.
- **Initial worktree:** `docs/RECRUITER-EVIDENCE.md` had a user-owned modification; it was not staged or changed.

## Decision and scope

The 2026-11-05 owner-approved teardown is the latest teardown decision. Its
reviewed Terraform plan destroyed four AKS resources; post-destroy checks found
the AKS cluster and its two resource groups absent. The current read-only
inventory also returns no AKS cluster. Do not run another destroy: AKS is
already absent, and separately scoped Azure resources remain. The full
execution history is in the [teardown runbook](../runbooks/azure-teardown-runbook.md#10-execution-record--2026-11-05).

The local `kind` inventory contains `local-platform`, but the configured
`kubectl` context is the former AKS context, not that kind cluster. No context
was changed and no cluster was touched. The old A13 Calico proof is on
`6470094`, not this base SHA, so A13 remains OPEN.

## Offline evidence on the base SHA

| Check | Command / environment | Result |
|---|---|---|
| Terraform formatting | `terraform fmt -check -recursive` (Terraform 1.16.3) | PASS, exit 0 |
| Terraform validation | `terraform -chdir=<root> validate -no-color` for `terraform/aks-foundation` and all four test-bearing modules | PASS, all five roots valid |
| Terraform native tests | `terraform -chdir=<root> test -no-color` for the same five roots | PASS, 16 passed, 0 failed (3 + 1 + 5 + 4 + 3). The tests use mock providers and plan assertions; this is not a cloud apply or runtime proof. |
| Platform Python tests | `python3 -m pytest -q tests` and `python3 -m pytest tests -q -o addopts=''` (Python 3.15.0) | PASS, 52 passed and 12 subtests passed; coverage run reported 86.74% against the configured 75% minimum |
| GitOps regression matrix | `python3 tests/test_gates.py` | PASS, 62 passed, 0 failed across G1-G16, including negative controls |
| Maintained Kustomize roots | `kubectl kustomize <root>` for each of the 10 roots listed below (kubectl 1.36.1 / Kustomize 5.8.1) | PASS, all rendered |
| Static policy/image gate | `python3 scripts/policy-gate.py` | PASS, 6 roots / 121 objects, maintained scope. Output states `digest_required=False`; this does not prove runtime image provenance. |
| Local GitOps source render | `python3 gitops/validate-gitops.py --repo-map gitops/repo-map.ci.yaml` | 38 PASS, 2 FAIL: the pinned CreditFlow and QuanLyKho checkouts are not present in this repository-local environment. No success-shaped fallback was accepted. |

Kustomize render counts:

| Root | Rendered resources |
|---|---:|
| `deploy/base` | 17 |
| `deploy/base/observability` | 26 |
| `deploy/overlays/aks-observability` | 26 |
| `deploy/overlays/dev` | 17 |
| `deploy/overlays/prod` | 18 |
| `deploy/overlays/validation` | 17 |
| `kubernetes/apps/langfuse` | 3 |
| `kubernetes` | 3 |
| `platform/envoy-gateway/gateway` | 7 |
| `platform/envoy-gateway/proof-backend` | 2 |

The repo-local GitOps failures are an environment limitation, not a passing
external render. On the exact base SHA, GitHub Actions checked out the pinned
external source revisions and completed the relevant CI runs successfully:

| Workflow | Result | URL |
|---|---|---|
| `pr-gate` (Python, security, Terraform, Kubernetes, console, SonarCloud jobs) | success | [run 42070399687](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42070399687) |
| `gitops-validate` (pinned external repositories and negative control) | success | [run 42070399926](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42070399926) |
| Source SBOM and Dependency Scan | success | [run 42070399700](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42070399700) |
| `oidc-azure` | success | [run 42070399516](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42070399516) |

The CI links prove those jobs on the base SHA only. They do not prove a live
AKS workload, Azure Monitor delivery, data migration, backup restore, cost
ceiling, or production approval.

## PR candidate CI

PR [#30](https://github.com/imtarget05/AKS-SRE-Platform/pull/30) was first
validated on candidate SHA `25b8e9f3e246f51251f77c8e5a44ae8cc34d9072`.
Its [PR-gate run](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42157000452)
passed the Kubernetes, security, Python, Terraform, and console jobs. SonarCloud
failed with `Not authorized`; no token value was inspected or changed. The
[source SBOM scan](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42157000461)
passed on the same candidate SHA. The SonarCloud check remains blocked on
credential/project authorization and must not be represented as a code pass.

## Azure inventory and evidence classification

Read-only queries ran against the Azure subscription selected by the local
Azure CLI. Results describe only that subscription and the permissions visible
to the signed-in identity.

| Area | Observed state | Classification and limit |
|---|---|---|
| AKS / VM / VMSS | `az aks list` and `az vm list` returned no clusters or VMs. The current resource listing contained no AKS/Compute resource; the teardown runbook says the AKS resource groups are absent. | **DEMONSTRATED — absent in the queried subscription.** Consumption output still included historical AKS VMSS meter references; those are not evidence of a current VM. |
| App Service | `az webapp list` returned no apps. | **DEMONSTRATED — none listed.** This does not classify the separately listed Container Apps as App Service. |
| Other app runtime | Container Apps `smartdoc-api` and `creditflow-api`, plus environment `cae-portfolio-env`, are listed in `rg-portfolio-prod`. | **DEMONSTRATED — resource inventory only.** This check did not verify revision health, business behavior, or release SHA. |
| Networking | `az network vnet list` returned no VNets. `NetworkWatcher_eastasia` remains in `NetworkWatcherRG`; no current AKS network resources were listed. | **DEMONSTRATED — inventory. LAB_ONLY — Terraform networking behavior**, whose four native tests use mocks. No live deny/allow or private-cluster path was tested. |
| Storage | Storage account `stakssre` remains in `rg-aks-tfstate` with `Standard_LRS`. Two ACRs also remain: `acrflashsalep6` and `crportfolioa3deec`. | **DEMONSTRATED — presence only. LAB_ONLY — design/tests.** No restore, retention, access-path, or workload-durability test was performed. |
| Azure Monitor / Log Analytics | Two `PerGB2018` workspaces are listed: `workspace-rgportfolioprodG5VV` and `DefaultWorkspace-a3deec78-7edb-41cd-9e94-ec1d4d9379f5-EA`. The read-only DCR list returned no rules. | **DEMONSTRATED — workspace inventory. NOT_YET — live AKS Monitor.** No AKS exists to associate or verify telemetry against; workspace presence does not prove ingestion or alert delivery. |
| Cost / budget | Budget list returned `[]`. Consumption rows included `None` values; the read-only CLI response could not be reliably aggregated into a current spend amount. Existing Container Apps, registries, workspaces, and Terraform state storage may still incur charges. | **NOT_YET.** No verified current monthly cost, approved cap, or demonstrated hard-stop behavior. Do not interpret absence of AKS as zero Azure spend. |
| Migration / backup / rollback | No current AKS runtime exists. The portfolio queue still requires QuanLyKho migration 034 with snapshot/rollback and same-release cloud proof for CreditFlow. The 2026-11-05 PostgreSQL dump is a separate local backup artifact, not proof of cloud restore or a migration release. | **NOT_YET.** No migration or restore was run in this offline task. |
| Security | Same-SHA CI security/SBOM jobs passed; local static policy and G1-G16 checks passed. | **LAB_ONLY — source/config gates. NOT_YET — runtime security.** No live identity, network-policy enforcement, Azure Monitor security signal, penetration test, or production threat validation was performed. |

## Portfolio checkpoint status

| Item | Status | Reason |
|---|---|---|
| A1 offline validation slice | **DEMONSTRATED** | Terraform fmt/validate/test, Python tests, Kustomize renders, repo-local policy checks, and exact-SHA CI are recorded above. This does not close a cloud gate. |
| A2 / A3 | **OPEN** | No current Azure runtime is available to establish runtime-dependent evidence. |
| C1 — cloud foundation/release | **OPEN; offline subset DEMONSTRATED** | Repo-local infrastructure tests and CI passed, but A13 needs a final-SHA capable-CNI proof; A16 runtime/state/cost/rollback remain open; QuanLyKho migration and Cloud release legs remain open. |
| C2 — business journeys and approvals | **OPEN** | Cloud API/UI/device journeys and bank-owned artifacts are not established by offline tests. |
| C3 — release closure | **OPEN** | No same-release cross-project evidence, cost/rollback reconciliation, or go-live signatures; the 2026-11-05 matrix remains 12/14, 0/21, 0/22 (28.57%), not above 90%. |
| C4 | **NOT_YET / undefined** | The current `tasks/plan.md` and `tasks/todo.md` define C0-C3 only. No C4 acceptance criteria were invented or scored. |
| Azure Monitor live | **OPEN** | Workspaces exist, but no current AKS/DCR association or live telemetry path was demonstrated. |

No portfolio score was changed by these offline checks. The unqualified
“production-grade” proof language in the architecture presentation was
replaced with wording that distinguishes implementation coverage from
production readiness. A2/A3, live Azure Monitor, A13, A16, and all runtime,
migration, cost, recovery, and approval-dependent evidence remain open.
