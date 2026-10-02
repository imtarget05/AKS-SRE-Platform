# CURRENT_STATE — Engineering Checkpoint

- **Updated:** 2026-10-02
- **Wave:** Execution Wave 1 = Phase A + B + C
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


## Next session starts at

**Phase D** — Terraform modularisation into
`modules/{network,aks,acr,keyvault,identity,monitoring}` with
`environments/{validation,prod}`, plus `*.tftest.hcl` asserting behaviour rather
than asserting "0 tests". The plan must not change what the existing
`terraform/aks-foundation` root produces; compare with `terraform show -json`.

## Open items carried into Wave 2

- `gitops/validate-gitops.py` hardcodes `~/Downloads/...` paths for two external
  repos and fails on day one. Needs an argument/env mapping, and CI must fail
  loudly on a missing external repo rather than silently skipping it.
- `python3` on the workstation resolves to `MAIA/.venv`. CI must own its
  environment explicitly.
- `tflint`, `kubeconform`, `conftest`, `k6`, `syft`, `cosign` are not installed
  locally; CI must install pinned versions and document them.
- `kubernetes/order-worker.yaml` (Service Bus) disagrees with
  `kubernetes/keda-autoscaler.yaml` (RabbitMQ); both belong to the FlashSale
  repo and are scheduled for supersede.
- `scripts/bootstrap.sh:38` applies a file that only exists as `.disabled`, so
  step 5/5 cannot run as written.
