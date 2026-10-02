# AKS-SRE-Platform — Current Tasks

> **Updated: 2026-10-02.** This file holds **one live section** only. Everything
> that used to be appended here as a new `ACTIVE GOAL` heading has been moved to
> [`../plans/history/`](../plans/history/) and is kept for the record, not for
> execution. Superseded sections are never deleted; they are moved and marked.

## LIVE — Execution Wave 1: Phase A done, B next

**Status: 🟡 IN PROGRESS.** Strategy changed on 2026-10-02: **AKS is the proof
surface, local kind is the OSS / dry-run profile.** The decision and its measured
capacity arithmetic are in
[`../docs/adr/014-azure-first-verification.md`](../docs/adr/014-azure-first-verification.md),
which supersedes ADR-013 in part. Live engineering checkpoint:
[`../docs/engineering/CURRENT_STATE.md`](../docs/engineering/CURRENT_STATE.md).

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

### Next, in order

1. **Phase B — CI gates.** `pr-gate.yaml` (fmt / validate / `terraform test` /
   tflint / kustomize render / kubeconform / policy / image pinning / Trivy),
   `gitops-validate.yaml`, `oidc-azure.yaml` with an environment-bound positive
   control and a negative control that must fail. Fix
   `gitops/validate-gitops.py` first — it hardcodes `~/Downloads` paths for two
   external repos and is red on day one. No badge until a real run is green.
2. **Phase C — Azure identity, ACR, state.** This repo gets its own Entra
   application and federated credentials, scoped by GitHub Environment. No
   client secret. Own tfstate account, Entra-only auth, `validation` and `prod`
   keys separate. ACR via Terraform. Budget alert attempted; if the API refuses,
   record `BUDGET_NOT_CREATED` and do not block.
3. **Phase D onwards** — Terraform modules + environments, then AKS validation
   apply, workload, observability, SLO, GitOps drift, identity proof,
   autoscaling, reliability, failure injection, security, supply chain,
   teardown, portfolio freeze.

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
