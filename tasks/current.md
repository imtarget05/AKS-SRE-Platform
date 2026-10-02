# AKS-SRE-Platform — Current Tasks

> **Updated: 2026-10-02.** This file holds **one live section** only. Everything
> that used to be appended here as a new `ACTIVE GOAL` heading has been moved to
> [`../plans/history/`](../plans/history/) and is kept for the record, not for
> execution. Superseded sections are never deleted; they are moved and marked.

## LIVE — Wave 1 in progress: Phase B + F foundation done, Phase C next

**Status: 🟡 IN PROGRESS.** Strategy changed on 2026-10-02: **AKS is the proof
surface, local kind is the OSS / dry-run profile.** The decision and its measured
capacity arithmetic are in
[`../docs/adr/014-azure-first-verification.md`](../docs/adr/014-azure-first-verification.md),
which supersedes ADR-013 in part. Live engineering checkpoint:
[`../docs/engineering/CURRENT_STATE.md`](../docs/engineering/CURRENT_STATE.md).

### Phase A — honesty layer: DONE (merged, `main` @ `7ca873e`)

### The three blockers from the audit no longer exist

All three were measured again on 2026-10-02:

- **Quota is free, not exhausted.** `az vm list-usage` reports `0/10` in both
  `eastus` and `eastasia`, because the 7A cluster was destroyed and released its
  nodes. ADR-013 read a transient state as a structural wall. No quota increase
  is required. The real ceiling is 10 vCPU, and the validation envelope is 8
  (system `1 × D2s_v6` + user `max 3 × D2s_v6`), leaving 2 vCPU.
- **The tfstate backend is gone.** `stflashs3ctfbk01` / `flashsale-prod-rg` are
  absent from this subscription; the only storage account is `sttfmaia`, which
  belongs to MAIA. There is no IP allowlist left to bypass and no state to
  inherit — this repo needs its own Entra-authenticated state identity.
- **AKS was already proven once.** `docs/evidence/phase7a/` holds 19 runtime
  gates, all PASS, including private ACR pull by digest and Workload Identity
  token exchange, with ≈ $0.20 compute and a full teardown.

### Phase A — honesty layer: DONE

- **ADR-013** — repaired a sentence split across the file and an alternatives
  table stranded after `Revisit when`; status changed to superseded in part.
- **ADR-014** — new. Azure-first verification, measured 10 vCPU constraint, the
  managed-observability profile, ELK as the local OSS profile, the
  single-log-sink rule, SLO baseline-before-threshold, transient validation.
- **README** — removed the false "no cluster has ever been successfully applied"
  claim in both places it appeared. Platform features are now split into
  *proven on AKS*, *proven on kind*, *defined but not proven*, and *known
  inconsistencies*.
- **EVIDENCE.md** — gained an environment vocabulary. Local rows are
  `PRE_AZURE_DRY_RUN`; `AZURE_VALIDATION` rows are added only when they exist.
  ELK and SLO non-claims stated with the numbers that justify them.

### Phase B — CI enforcement: DONE (PR #1, branch `aks-sre/phase-b-ci`)

Three workflows, all executed on GitHub Actions. Green except one deliberate red.

- `gitops/validate-gitops.py` rewritten. It resolved two external repos to
  `~/Downloads` paths and so could never run in CI; it now validates repo-owned
  objects, takes external checkouts from `--repo-map`, rejects machine-specific
  paths as a usage error, and reports absent external trees as
  `EXTERNAL_REPO_NOT_PRESENT` — never as a pass. 17-assertion test matrix run as a
  subprocess.
- `MANIFEST-INVENTORY.md` classifies every manifest; an unclassified YAML fails
  CI. Four of the six files under `kubernetes/` are undeployable as written or
  contradict each other, and kustomize renders them green anyway.
- `scripts/policy-gate.py`: probes, resources, securityContext, topology spread
  and image pinning over `deploy/`. `:latest` is rejected now; digests become
  mandatory in Phase O.
- `pr-gate.yaml`: whole-repo `fmt`, `init -backend=false`, `validate`, `tflint`,
  `terraform test`, kustomize render, kubeconform, inventory, policy gate, Trivy.
- `oidc-azure.yaml`: contract is enforced; the live job is **skipped** and reports
  `OIDC_LIVE_LOGIN = NOT_VERIFIED` in the run summary.

`terraform test` is red with `TERRAFORM_NATIVE_TESTS = NOT_IMPLEMENTED`. The root
cannot be planned offline because `main.tf:112` and `outputs.tf:22` index a
computed block that `mock_provider` leaves empty and `override_resource` cannot
populate. A 12-assertion suite was written and reverted: a suite that cannot run
is a claim, not a test. The assertion-count check must survive until Phase D.

### F foundation — repo-owned workload: DONE

`app/sre-demo-api` plus `deploy/base` and `deploy/overlays/validation`. Until now
every Kubernetes claim in this repo was measured against a workload owned by
another repository. 7 unit tests pass; the probe split is the load-bearing part
(`/health/live` never touches the dependency, `/health/ready` does), and
`/api/fail` is physically unreachable unless the validation overlay arms it.

Rendering the overlay surfaced a real bug: `FAILURE_INJECTION_ARMED` was declared
as an explicit `env` entry, which takes precedence over `envFrom` and would have
made the overlay's ConfigMap unable to arm it.

### Phase C — State isolation: DONE (2026-10-02)

Isolated state backend provisioned in `rg-aks-tfstate/stakssre` (container `tfstate`), using Azure AD authentication (`use_azuread_auth = true`) and completely separated from MAIA storage.

### Phase D — Terraform module decoupling & tests: DONE (2026-10-02)

Decoupled cluster creation (`terraform/modules/aks_cluster`) from the ACR role assignment boundary (`terraform/modules/acr_attachment`). No `try(..., "mock-object-id")` fallback needed. `terraform test` runs offline with mock providers and passes with semantic assertions locally and in GitHub Actions CI (PR #1).

### Phase E — Transient AKS Validation: IN PROGRESS (2026-10-02)

Transient AKS apply running against subscription `a3deec78` in `eastasia` within the measured 10 vCPU quota constraint (1 system node `Standard_D2s_v6` + 1 user node `Standard_D2s_v6` = 4 vCPU). Capturing live workload identity, workload readiness, and failure recovery evidence before immediate teardown.

### ⛔ STOP conditions

- **No `terraform apply`** against any environment until each one has a saved,
  reviewed plan and explicit approval. Cost Safety Mode still applies; the
  validation cluster is transient and must be destroyed after evidence capture.
- **No fabricated SLO history.** Targets are `PROPOSED` until an Azure baseline
  is measured; `PRODUCTION_30_DAY_HISTORY = NOT_AVAILABLE`.
- **No claim without evidence**, and **no environment relabelling**: a kind
  result is never published as Azure evidence.
- **No `git add .` / `git add -A`.** Selective staging, no force-push.
- **Do not delete `docs/evidence/**` or `plans/**`.** Superseded is not the
  same as worthless.
