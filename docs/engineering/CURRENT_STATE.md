# CURRENT_STATE — Engineering Checkpoint

- **Updated:** 2026-10-02 (after Phase B CI enforcement and the Phase F workload foundation)
- **Wave:** Execution Wave 1 = Phase A + B + C
- **Branch:** `aks-sre/phase-b-ci` → PR #1. Phase A is merged on `main` at `7ca873e`.
- **Strategy:** Azure-first. AKS is the proof surface; local kind is the OSS /
  dry-run profile. See
  [`../adr/014-azure-first-verification.md`](../adr/014-azure-first-verification.md).
- **Canonical task list:** [`../../tasks/current.md`](../../tasks/current.md)

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
| HPA / AKS Cluster Autoscaler | — | **NOT RUN** |
| Enforced NetworkPolicy (Cilium) | — | **NOT RUN** |
| PDB / drain / topology spread | — | **NOT RUN** |
| Continuous CI (`.github/`) | — | **ABSENT** |
| `terraform test` / tflint | — | **ABSENT** |
| Repo-owned workload (`app/sre-demo-api`) | — | **ABSENT** |

## Measured constraints (2026-10-02 — do not re-litigate without re-measuring)

- **Regional vCPU ceiling: 10**, currently **0/10 used**. The 7A cluster was
  destroyed, so the quota ADR-013 treated as a wall is free. Verify:
  `az vm list-usage --location eastus -o tsv | head -3`
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
| Gate test matrix G1–G9 | `IMPLEMENTED_TESTED` | 17 assertions, run as a subprocess so the exit code under test is the real one |
| Kubernetes render + kubeconform | `IMPLEMENTED_TESTED` | `Valid: 13, Invalid: 0` per root; 26 objects across 2 roots |
| Manifest inventory | `IMPLEMENTED_TESTED` | M-B6 orphan detected and rejected |
| Static policy + image gate | `IMPLEMENTED_TESTED` | `POLICY GATE PASS: 2 kustomize root(s), 26 object(s)` |
| Terraform fmt / init / validate / tflint | `IMPLEMENTED_TESTED` | whole-repo fmt clean, `-backend=false` init, validate Success, tflint 0 issues |
| Trivy config + secret scan | `IMPLEMENTED_TESTED` | clean at HIGH/CRITICAL, every ignore carrying a written justification |
| OIDC workflow contract | `IMPLEMENTED_TESTED` | static checks pass |
| OIDC live login / negative live | `NOT_VERIFIED` | `live` job **skipped**; no identity exists yet (Phase C) |
| **`terraform test`** | **`NOT_IMPLEMENTED`** | collects 0 assertions. The only red step in CI, by design |
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

### The one red job, and why it stays red

`TERRAFORM_NATIVE_TESTS = NOT_IMPLEMENTED`. `terraform test` cannot evaluate
`terraform/aks-foundation` offline: `main.tf:112` and `outputs.tf:22` index
`azurerm_kubernetes_cluster.aks.kubelet_identity[0]`, a computed nested block that
`mock_provider` returns empty and that `override_resource` cannot populate
(verified on Terraform 1.16.3, both at the top level and inside a `run` block).
A 12-assertion suite was written and reverted, because a suite that cannot
execute is a claim, not a test. Phase D resolves it. The assertion-count check
must not be deleted to make the job green.

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

- `terraform test` collects zero assertions (`TERRAFORM_NATIVE_TESTS`).
- `kubernetes/order-worker.yaml` (Service Bus) disagrees with
  `kubernetes/keda-autoscaler.yaml` (RabbitMQ); both are classified in
  `MANIFEST-INVENTORY.md` as legacy and belong to the FlashSale repo.
- `scripts/bootstrap.sh:38` applies a file that only exists as `.disabled`, so
  step 5/5 cannot run as written.
- `conftest`, `k6`, `syft`, `cosign` are still absent; they arrive with the
  policy, load-test and supply-chain phases.
- No `runbooks/`, `alerts/` or `dashboards/` directory exists yet. They are not
  created until a capability needs them.

