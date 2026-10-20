# CURRENT_STATE — Engineering Checkpoint

- **Updated:** 2026-10-20 (after the LegacyApp subtree import and A0.1 honesty pass)
- **Wave:** Execution Wave 1 = Phase A + B + C
- **Branch:** `aks-sre/phase-b-ci` → PR #1. Phase A is merged on `main` at `7ca873e`.
- **Strategy:** Azure-first. AKS is the proof surface; local kind is the OSS /
  dry-run profile. See
  [`../adr/014-azure-first-verification.md`](../adr/014-azure-first-verification.md).
- **Canonical task list:** [`../../tasks/current.md`](../../tasks/current.md)

> **A0 state:** `apps/legacy-inventory/` was imported with preserved history
> and passed local subtree gates. It remains a reference workload; its `/sync`
> endpoint is a no-op simulation, not an inventory integration. The maintained
> Argo Application source switch and every live cluster operation remain
> unapproved. See ADR-015 and `docs/evidence/a0-legacyapp-subtree-import.md`.

## Where the project actually is

| Capability | Environment | State |
|---|---|---|
| AKS foundation: system pool, OIDC issuer, Workload Identity, `Manual` node provisioning | `AZURE_VALIDATION` | **PASS** 2026-09-21, then stopped + torn down |
| User-pool placement isolation | `AZURE_VALIDATION` | **PASS** 2026-09-21, pool since deleted |
| Private ACR pull by digest, no `imagePullSecret` | `AZURE_VALIDATION` | **PASS** 2026-09-21 |
| Workload Identity federated token exchange + scoped read | `AZURE_VALIDATION` | **PASS** 2026-09-21, identities since deleted |
| Argo CD sync + `git revert` rollback + drift detect/reconcile | `PRE_AZURE_DRY_RUN` | **PASS** on kind |
| Gateway API + Envoy Gateway shared north-south | `PRE_AZURE_DRY_RUN` | **PASS** on kind |
| Prometheus + Grafana + one real alert fire/resolve cycle | `PRE_AZURE_DRY_RUN` | **PASS** on kind |
| HPA / AKS Cluster Autoscaler | — | **NOT RUN** (HPA manifest validated by kubeconform; no scale event observed) |
| Enforced NetworkPolicy (`network_policy = "azure"`) | `AZURE_VALIDATION` | Deployed 2026-10-02; default-deny + allow rules applied; deny-of-unauthorized-traffic **NOT MEASURED** (no negative-traffic probe run) |
| PDB / drain / topology spread | — | **NOT RUN** (PDB manifest schema-valid; no drain event) |
| Continuous CI (`.github/`) | GitHub Actions | **PASS** (Workflows run & pass 100% green on PR #1) |
| `terraform test` / tflint | Local & CI | **PASS** (Decoupled modules tested offline with semantic assertions) |
| Repo-owned workload (`app/sre-demo-api`) | Node.js / K8s | **IMPLEMENTED_TESTED** (Unit tests pass; probes & failure injection decoupled) |

## Measured constraints (2026-10-02 — do not re-litigate without re-measuring)

- **Regional vCPU ceiling: 10**, currently **0/10 used**. The 7A cluster was
  destroyed, so the quota ADR-013 treated as a wall is free. Verify:
  `az vm list-usage --location eastasia -o tsv | head -3`
- **Validation capacity envelope: 8 vCPU** — system pool `1 × D2s_v6` (2) +
  user pool `max 3 × D2s_v6` (6). Leaves **2 vCPU** for observability and for
  the cluster-autoscaler proof. `D4s_v6` is out: 2 × D4s_v6 consumes 8 vCPU for
  the system pool alone.
- **The old tfstate backend does not exist.** `stflashs3ctfbk01` /
  `flashsale-prod-rg` are absent from this subscription. `az group list` shows
  only `NetworkWatcherRG`, `rg-portfolio-evidence`, `rg-maia-tfstate`,
  `rg-maia-verify`. The only storage account, `sttfmaia`, belongs to **MAIA** —
  do not inherit it. This repo needs its own Entra-authenticated state identity
  with `validation` and `prod` keys kept separate.
- **Azure-first is a shared quota.** Other portfolio repos draw on the same
  10 vCPU. A second AKS environment here needs a quota increase first.
- **The 2 vCPU remainder is not "free observability capacity."** It must also
  carry the Cluster Autoscaler proof. The two are therefore run as
  **sequential experiment profiles**, never assumed to coexist:
  `PROFILE A` = autoscaler validation + the minimum telemetry needed to observe
  it; `PROFILE B` = observability/SLO validation + the normal workload
  topology. A claim must name the profile it was measured under, and must never
  state that both stacks ran simultaneously unless they actually did.

## Locked decisions — do not drift

1. **One log sink per profile.** Azure overlay: Fluent Bit → Log Analytics. OSS
   overlay: Fluent Bit → Logstash → Elasticsearch → Kibana. Never both. The
   application injects `trace_id`/`span_id` into its structured log before
   shipping; the sink does not create correlation.
2. **ELK is `IMPLEMENTED_TESTED_LOCAL` / `NOT_APPLIED_ON_AKS_QUOTA`.** A 2 GiB
   Elasticsearch heap is ≈2 vCPU, and the envelope has 2 vCPU total, already
   owed to Prometheus + OTel Collector + synthetic prober. A measured capacity
   decision, not unfinished work. Revisit only on a quota increase.
3. **SLO lifecycle: `PROPOSED → BASELINE_MEASURED → TARGET_JUSTIFIED →
   DEFINED_AND_TESTED`.** Availability 99.9%, p95 < 500 ms, 5xx < 1%,
   recovery < 120 s are hypotheses. Measure the Azure baseline first.
4. **`PRODUCTION_30_DAY_HISTORY = NOT_AVAILABLE`.** No fabricated SLO history.
5. **Burn rate uses error-budget semantics:**
   `burn_rate = observed_error_ratio / (1 - SLO)`, as a short/long window pair —
   fast `5m + 1h`, slow `30m + 6h`. 14.4 / 6 apply only while the policy is
   99.9%. Never substitute a bare `error_rate > N`.
6. **Azure capacity is transient.** Apply → prove → destroy. Cost Safety Mode
   stays on. A budget alert is alerting, not a hard ceiling.
7. **Alerts must prove firing and resolving**, with MTTD / MTTR recorded and a
   runbook link. A rule file that exists is not evidence.
8. **The laptop is an authoring surface.** No claim may depend on the Docker
   Desktop memory cap.

## Standing STOP conditions

- **No `terraform apply`** against any environment without a saved, reviewed
  plan and explicit approval.
- **No `git add .` / `git add -A`.** Selective staging only. No force-push.
- **Do not delete `docs/evidence/**` or `plans/**`.** Superseded ≠ worthless.
- **No claim without evidence.** Every assertion in `README.md` /
  `docs/EVIDENCE.md` maps to a file, a command and a commit.
- **Do not relabel an environment.** A kind result is never published as Azure
  evidence.
- **A CI gate is not "verified" because the script exists.** It is verified when
  a real workflow run collected the intended tests, the negative control bit,
  and the gate failed for the intended reason before being restored to green.

| SLO / error budget / burn-rate alerting | — | **NOT DEFINED** |
| Pod → Key Vault secret read | — | **NOT RUN** |


## Phase B and the F workload foundation — IMPLEMENTED_TESTED (2026-10-02)

Measured on GitHub Actions, PR #1, branch `aks-sre/phase-b-ci`. Every status
below comes from a run log, not from the existence of a file. One step is red,
by design; everything else is green.

| Control | Status | Evidence from the run log |
|---|---|---|
| GitOps validator, repo-owned semantics | `IMPLEMENTED_TESTED` | `GITOPS: 16 passed, 0 failed, 2 not-present, 18 total` |
| GitOps negative control (M-B1) | `IMPLEMENTED_TESTED` | `M-B1 confirmed: validator rejected the mutation (rc=1)`, then `git diff --exit-code` clean |
| Gate test matrix G1–G10 | `IMPLEMENTED_TESTED` | 24 assertions, run as a subprocess so the exit code under test is the real one |
| Kubernetes render + kubeconform | `IMPLEMENTED_TESTED` | `Valid: 13, Invalid: 0` per root; 26 objects across 2 roots |
| Manifest inventory | `IMPLEMENTED_TESTED` | M-B6 orphan detected and rejected |
| Static policy + image gate | `IMPLEMENTED_TESTED` | `POLICY GATE PASS: 2 kustomize root(s), 26 object(s)` |
| Terraform fmt / init / validate / tflint | `IMPLEMENTED_TESTED` | whole-repo fmt clean, `-backend=false` init, validate Success, tflint 0 issues |
| Trivy config + secret scan | `IMPLEMENTED_TESTED` | clean at HIGH/CRITICAL, every ignore carrying a written justification |
| OIDC workflow contract | `IMPLEMENTED_TESTED` | static checks pass |
| OIDC live login / negative live | `NOT_VERIFIED` | `live` job **skipped**; no identity exists yet (Phase C) |
| **`terraform test`** | **`IMPLEMENTED_TESTED`** | 5 passing run blocks across 3 roots (`aks-foundation` 2, `acr_attachment` 1, `aks_cluster` 2). CI executes **all three** roots as of 2026-10-20 (it previously ran only `aks-foundation` = 2) |
| Azure mutation | none | no Azure resource created by this branch |

Five consecutive Actions runs were needed to reach this state, and every one found
something no local check could: three distinct `trivy-action` failures before it
scanned anything, a kubeconform download that wrote an HTML error page and failed
two lines later with an opaque tar message, and a `case` statement truncated by an
earlier edit. None were visible until the workflows actually ran, which is the
argument for requiring a real run rather than treating a workflow file as evidence.


### A finding that only surfaced because the lint step was moved

tflint had never actually executed before, because it sat after the always-failing
`terraform test` step and reported as *skipped* on every run. Once moved ahead of
it, tflint immediately reported one real issue: `variables.tf` declared
`workload_identity_client_id` and no resource referenced it. `terraform validate`
passes anyway, which is the point — an unread input looks identical from the
outside to one that is wired up and working. Removed, with a note recording what
it was.

This is the general lesson, and it is worth stating because it will recur: **a
control placed after a step that is currently red is not a control.** Wherever a
known-failing gate exists, every other check in that job must run before it.

### Phase D — Module Decoupling and Terraform Native Tests: RESOLVED (2026-10-02)

`TERRAFORM_NATIVE_TESTS = PASS`. The computed block limitation was resolved cleanly in Phase D by decoupling the role-assignment boundary (`modules/acr_attachment`) from the core cluster definition (`modules/aks_cluster`). 

Because cluster creation does not inline the ACR role assignment, `modules/aks_cluster` and `terraform/aks-foundation` can be tested 100% offline with `mock_provider` without any fake fallbacks (`try(..., "mock-object-id")`) that would obscure true runtime dependencies. The native test suite (`tests/aks_foundation.tftest.hcl`) now passes with verified semantic assertions covering cluster naming, sizing (`Standard_D2s_v6`), OIDC issuer, and workload identity flags.

### Two tools that had to be replaced, not just pinned

- `aquasecurity/trivy-action` failed three consecutive runs before scanning
  anything: its tag needed a `v` prefix, then its bundled installer failed
  fetching trivy v0.65.0, then `trivy-version` turned out not to be a real input
  (it is `version`). Trivy is now installed and invoked directly, pinned, so the
  CI command is identical to the one run locally.
- kubeconform was downloaded with `curl -sSL`, which writes an HTML error page
  instead of failing, so a bad URL surfaced two lines later as an opaque tar
  error. Now `-f`, on v0.8.0, with SHA256 verification against the release
  CHECKSUMS file.

### Next session starts at

**Phase C** — repo-owned Azure identity, state and registry. No MAIA identity or
MAIA state may be reused. Then **Phase D**, which also closes the red
`TERRAFORM_NATIVE_TESTS` job described above.

Do not start Phase D's module split before Phase C, and do not run any
`terraform apply` before each environment has a saved, reviewed plan.

## Open items

### Closed on 2026-10-02 (Phase B + F foundation)

- ~~`validate-gitops.py` hardcodes `~/Downloads/...`~~ — rewritten; mappings come
  from `--repo-map`, machine-specific paths are a usage error, and external trees
  report `EXTERNAL_REPO_NOT_PRESENT`.
- ~~CI must own its Python environment~~ — `actions/setup-python` 3.12 with
  `requirements.lock` installed under `--require-hashes`.
- ~~tflint / kubeconform not installed locally~~ — CI installs both, pinned;
  kubeconform additionally checksum-verified.
- ~~No orphan manifests~~ — `MANIFEST-INVENTORY.md`, enforced by the validator.

### Still open

- ~~`terraform test` collects zero assertions (`TERRAFORM_NATIVE_TESTS`).~~
  **Resolved (Phase D)** and re-verified 2026-10-20: `terraform test` runs 5 run
  blocks across `aks-foundation` (2), `acr_attachment` (1), `aks_cluster` (2),
  all passing. This line was stale, not a live gap.
  **Further corrected 2026-10-20 (G2):** the 5 blocks were all passing locally,
  but CI executed only the 2 in `aks-foundation` — the job's
  `working-directory` meant the two module-level `*.tftest.hcl` files were never
  run by any CI step, and the `grep '[0-9]+ passed'` guard saw `2`, not `0`, so
  the guard passed while 3 assertions were invisible. CI now walks every root
  declared in `env.TERRAFORM_TEST_ROOTS`, prints a per-root count, and the
  guard consumes the total (`5`). The gate matrix also gained G10 assertions
  that fail if a root is dropped from CI, if a new module with a `*.tftest.hcl`
  is not wired in, or if the tflint lint loses its absolute `--config`.
- `tflint` covered only `terraform/aks-foundation` (job `working-directory`); the
  other 3 roots were never linted and no AzureRM ruleset was enabled.
  **Fixed 2026-10-20 (G2):** `terraform/.tflint.hcl` pins the `azurerm` plugin
  (v0.32.0) and the lint runs from `terraform/` with an **absolute**
  `--config` — a relative path hard-fails in 9 subdirectories, and omitting
  `--config` silently falls back to the bundled ruleset and *misses* AzureRM
  findings. Local result: 0 issues across all 10 directories.
  **Resolved (2026-10-20):** `terraform/.tflint.hcl` is tracked in commit
  `6b563d1`; a fresh runner can initialize the pinned plugin and the cache key
  incorporates the configuration file.
- `kubernetes/order-worker.yaml` (Service Bus) disagrees with
  `kubernetes/keda-autoscaler.yaml` (RabbitMQ); both are classified in
  `MANIFEST-INVENTORY.md` as legacy and belong to the FlashSale repo.
- ~~`scripts/bootstrap.sh:38` applies a file that only exists as `.disabled`, so
  step 5/5 cannot run as written.~~ **Fixed 2026-10-20** — applies the maintained
  `platform/argocd/applications/` and no longer applies the four manifests that
  `MANIFEST-INVENTORY.md` classifies as undeployable.
- ~~`platform/observability/*` was labelled `RENDERED` but no `kustomization.yaml`
  existed under `platform/`, so pr-gate never validated it.~~ **Corrected
  2026-10-20** — relabelled `REFERENCE_NOT_RENDERED`; the two `envoy-gateway`
  roots gained real kustomizations so their claim is now produced by CI.
- `conftest`, `k6`, `syft`, `cosign` are still absent; they arrive with the
  policy, load-test and supply-chain phases.
- No `runbooks/`, `alerts/` or `dashboards/` directory exists yet. They are not
  created until a capability needs them.

