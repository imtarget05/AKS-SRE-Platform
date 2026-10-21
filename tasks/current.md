# AKS-SRE-Platform — Current Tasks

> **Updated: 2026-10-21** (re-verification of the `recovery/g2-20261020`
> branch, tip `d628250`; previous update: 2026-10-20, tip `7801901`).
> Previous update: 2026-10-02.
> This file holds **one live section** only. Everything
> that used to be appended here as a new `ACTIVE GOAL` heading has been moved to
> [`../plans/history/`](../plans/history/) and is kept for the record, not for
> execution. Superseded sections are never deleted; they are moved and marked.

## LIVE — 2026-10-21: re-verification at tip `d628250` (stale claims corrected)

**Status: 🟡 LOCAL platform green · ⚠️ AZURE path needs a decision on the
terraform backend · ⏳ awaiting merge.**
**Branch:** `recovery/g2-20261020` (HEAD `d628250`) · **base:** `main` @
`0a92f58` (unchanged — the integration is a `--ff-only` fast-forward, verified).
**Branch size at this tip:** 9 commits / 24 files / `+25079 −201` on top of
`main` — **including** the 1 MB raw API dump
`docs/evidence/live-aks-2026-10-20/kubectl-cluster-info.txt`; excluding it,
8 commits / 18 files / `+2426 −195`.
**Full evidence:**
[`../docs/evidence/local-platform/2026-10-20-reverify.md`](../docs/evidence/local-platform/2026-10-20-reverify.md)
(§15 = the 2026-10-21 re-verification) ·
**Merge note:**
[`../docs/evidence/local-platform/2026-10-20-merge-note.md`](../docs/evidence/local-platform/2026-10-20-merge-note.md)
(§1.0 = the tip move).

### What was fixed today (each with a failing-before / passing-after test)

| ID | Defect | Fix | Gate |
|---|---|---|---|
| **F1** | the Argo CD install was applied **client-side** → it replaced the CRDs and destroyed existing custom resources | `scripts/bootstrap.sh` applies `--server-side --force-conflicts` | G13 |
| **F2** | two files owned the `grafana-dashboard-local-platform` ConfigMap → the second **overwrote and lost** a dashboard | one file is now the single owner, the other documents that it no longer owns it — **no dashboard dropped** | G13 |
| **F3** | the GitOps validator iterated over **one** project file and silently skipped the rest | every project file is validated | G11 |
| **F4** | a **second** `AppProject` with a wildcard allowlist existed (`gitops/projects/portfolio.yaml`) | duplicate names are a hard failure; the duplicate file is deleted | G11 |
| **F5** | Argo CD was installed from the **floating `stable` branch** while the docs claimed a pin | the pin lives in exactly one place — `platform/argocd/VERSION` = **v3.5.5** — and the installer *asserts* the running image matches it | G12 |

### What was fixed on 2026-10-21 (the re-verification)

| ID | Defect | Fix | Gate |
|---|---|---|---|
| **F6** | **`npm start` in `app/sre-demo-api` was a no-op** — `package.json` pointed at `src/server.js`, which only *exports* `createServer` and never calls `listen()`, so the process exited immediately and `curl /health` returned `000`. The **Dockerfile** (`CMD ["node","src/index.js"]`) was already correct, so the image worked while the script did not. | `package.json` → `"start": "node src/index.js"`; verified `npm start` → `curl /health` = **200**, `npm test` still **7/7** | **G14** (new) |

**Three stale evidence claims were corrected** (the branch tip had moved to
`d628250` and the machine state had changed) — the commit counts, the "no Azure
session" statement, and the "56 objects, 0 failures" dry-run count. See
§15.2 of the evidence document for the before/after of each.

### Cluster state today (local kind `local-platform`, **point-in-time**)

**Re-checked 2026-10-21** on the same cluster instance (13 h old), with the
context pinned — see §15.4 of the evidence document for the ambient-context
hazard:

- 3/3 nodes Ready (v1.36.1); Argo CD **7/7 Running** at the pinned **v3.5.5**
  (3 restarts each, from the Docker daemon crashes below).
- Application **`flashsale` → `Synced` / `Healthy`** — unchanged from
  2026-10-20, **at the time of the ~10:5x check**. ⚠️ **End state after this
  run: DEGRADED** — the Docker daemon crashed 6× during the 2026-10-21
  re-verification; after the last restart the nodes are Ready but
  `flashsale` is `Synced / Progressing`, `order-api` is crash-looping and
  `rabbitmq-0` never finishes booting. Cause: the daemon crash re-creates
  every pod sandbox and the data tier does not recover. **Not a repository
  regression** — no manifest/image/cluster object was changed. Recovery is a
  cluster mutation and was **not** performed (evidence §15.5).
- **Self-heal verified for spec drift (~1 s) and for a deleted resource
  (~1 s).**
- **FINDING — not a pass:** Argo CD v3.5.5 does **not** diff extra
  `metadata.labels`, so a hand-added label is **not** reverted (see §10 of the
  evidence document). **Self-heal is NOT verified for extra metadata labels.**
- **NEW (2026-10-21) — the manifest dry-run count is cluster-dependent:** the
  §2.3 scope (56 objects) server-dry-runs **56 pass / 0 fail** on 2026-10-20
  and **53 pass / 3 fail** on 2026-10-21. Cause (measured): the synced
  upstream `flashsale` application already owns the `order-worker` workload,
  so KEDA's admission webhook rejects this repo's legacy
  `ScaledObject/order-worker-scaler`. **The legacy `kubernetes/` root does not
  server-dry-run cleanly on a cluster where the upstream app is synced** —
  coexistence decision open, owner P03 (evidence §2.3.1).

### What is still NOT verified (never claim these)

- **Azure: nothing — by the 2026-10-20 recovery session.** No `az login`, no
  `terraform apply` **in that session**; the remote-state backend does not
  resolve from this machine (NXDOMAIN), so `terraform plan` against the real
  backend could not be attempted. The 5 `terraform test` assertions are
  **offline `mock_provider`** runs.
  > **Corrected 2026-10-21.** An Azure session **does** exist today
  > (`az account show` → `state: Enabled`) and **another actor** ran a live-AKS
  > create/destroy cycle, recorded in
  > `../docs/evidence/live-aks-2026-10-20/` and **audited** in §15.3 of the
  > evidence document. It is **not adopted** here: its apply/destroy steps
  > carry no committed command output and its "3 nodes Ready" claim is
  > contradicted by the node file committed next to it. The **end state** (the
  > cluster is gone, nothing left running) is confirmed by read-only `az`.
- **`legacyapp` Application** — not deployed, by design (`APPLY_LEGACYAPP=1`
  not set; ADR-015 source switch unapproved).
- **Business E2E / concurrency flow** — not re-run; only the deployment plane
  was proven.
- **`sre-demo-api` RED metrics on a pod** — the image reference points at a
  destroyed ACR registry.
- **A second Argo CD control plane in the `default` namespace** — pre-existing,
  not fixed, needs an explicit decision.

### Open items and owners (full table: §11 of the evidence document)

| # | Item | Owner |
|---|---|---|
| 1 | Azure path: session exists today but the **terraform backend was switched `azurerm` → `local`** by `d628250` and the remote state `aks-sre/validation.terraform.tfstate` is now **orphaned** — restore the remote backend or document it as abandoned | P03 |
| 2 | `legacyapp` Application never deployed | P03 + ADR-015 approver |
| 3 | business E2E / concurrency not re-run | P01 + P03 |
| 4 | `sre-demo-api` pod-level RED metrics | P03 |
| 5 | second Argo CD install in `default` | P03 |
| 6 | Docker Desktop crashed 3× → host is not a stable measurement surface | host / DevOps |
| 7 | the kind cluster is a **disposable artifact** → runtime claims are point-in-time; isolate it into its own Docker context / VM | platform / process |
| 8 | finding: extra `metadata.labels` are not self-healed (§10) | P03 |
| 9 | `tflint` not installable from Homebrew (worked around with the release binary; CI unaffected) | P03 tooling |
| 10 | 2 × `EXTERNAL_REPO_NOT_PRESENT` in the GitOps validator | P03 |
| 11 | **NEW 2026-10-21:** the repo's legacy `kubernetes/` root does not server-dry-run cleanly next to the synced upstream app (3 of 56 objects rejected by the KEDA webhook) — coexistence decision | P03 |
| 12 | **NEW 2026-10-21:** the **kubeconfig `current-context` on this machine is the destroyed `aks-portfolio-dev`**, not `kind-local-platform` — always pin `--context` (the machine's kubeconfig was **not** modified) | machine owner |
| 13 | **NEW 2026-10-21:** `docs/evidence/live-aks-2026-10-20/aks-live-evidence.md` still says "AZURE_CLOUD_VERIFIED" unqualified, and its "3 nodes Ready" claim is contradicted by its own `kubectl-nodes.txt` (1 node, v1.36.4) — audit addendum appended | P03 / author of `d628250` |

### Next step (owned by whoever integrates — **nothing was merged or pushed**)

Follow §3 of the merge note: re-check that `main` is still `0a92f58`, run the
three gates, then `git merge --ff-only recovery/g2-20261020`, re-run the gates,
and re-bootstrap the cluster (a cluster mutation — needs an explicit
go-ahead).

---

## (no longer live) Wave 1 in progress: A0 subtree import complete, source switch pending approval

**Status: 🟡 IN PROGRESS.** Strategy changed on 2026-10-02: **AKS is the proof
surface, local kind is the OSS / dry-run profile.** The decision and its measured
capacity arithmetic are in
[`../docs/adr/014-azure-first-verification.md`](../docs/adr/014-azure-first-verification.md),
which supersedes ADR-013 in part. Live engineering checkpoint:
[`../docs/engineering/CURRENT_STATE.md`](../docs/engineering/CURRENT_STATE.md).

> **Kept for the record — this is no longer the live section.** The live
> section for 2026-10-20 is above. Everything under this heading is the
> 2026-10-02 state, kept unchanged so the reasoning that produced it stays
> auditable. Where it is now stale, it is marked **stale as of 2026-10-20**
> at the point of staleness — nothing below was rewritten.

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

`terraform test` is **green** as of 2026-10-20: 5 run blocks across 3 roots
(`aks-foundation` 2, `acr_attachment` 1, `aks_cluster` 2), and CI now executes
all three roots — it previously ran only `aks-foundation` (2 blocks), so the
`TERRAFORM_NATIVE_TESTS` guard was reading `2` while 3 assertions were never
executed. The guard is now fed the total across roots and still fails on `0`.
The root cannot be planned offline because `main.tf:112` and `outputs.tf:22`
index a computed block that `mock_provider` leaves empty and `override_resource`
cannot populate. A 12-assertion suite was written and reverted: a suite that
cannot run is a claim, not a test. The assertion-count check must survive until
Phase D.

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

> **Stale as of 2026-10-21.** The backend was **switched to `local`** in
> `terraform/aks-foundation/versions.tf` by commit `d628250` ("reconfig'd for
> local evidence run") and the switch was **committed and not reverted**. The
> state backend described above still exists, but the repository no longer
> points at it, so it is now **orphaned** — a later `terraform apply` will not
> read it. Restoring the remote backend, or documenting it as deliberately
> abandoned, is an **open decision** (owner P03; evidence §15.3b). The
> historical fact above (that the isolated backend was provisioned on
> 2026-10-02) is unchanged.

### Phase D — Terraform module decoupling & tests: DONE (2026-10-02)

Decoupled cluster creation (`terraform/modules/aks_cluster`) from the ACR role assignment boundary (`terraform/modules/acr_attachment`). No `try(..., "mock-object-id")` fallback needed. `terraform test` runs offline with mock providers and passes with semantic assertions locally and in GitHub Actions CI (PR #1).

### Phase E — Transient AKS Validation: IN PROGRESS (2026-10-02)

> **Stale as of 2026-10-20.** No AKS cluster was applied, measured or re-run
> during the 2026-10-20 recovery work. The Azure path was not touched at all:
> no `az login`, no `terraform apply`, and the remote-state backend does not
> resolve from this machine (NXDOMAIN), so `terraform plan` against the real
> backend cannot be attempted here. Treat Phase E as **not currently running**
> and its runtime claims as **historical, not re-verified**. See the live
> section above and §11 of
> [`../docs/evidence/local-platform/2026-10-20-reverify.md`](../docs/evidence/local-platform/2026-10-20-reverify.md).

Transient AKS apply running against subscription `a3deec78` in `eastasia` within the measured 10 vCPU quota constraint (1 system node `Standard_D2s_v6` + 1 user node `Standard_D2s_v6` = 4 vCPU). Capturing live workload identity, workload readiness, and failure recovery evidence before immediate teardown.

### A0 — LegacyApp subtree import: PASS locally (2026-10-20)

- Imported committed `Productionized-LegacyApp/main` history without squash into `apps/legacy-inventory/` at platform commit `8c0f66c`.
- Carried over the current LegacyApp observability working diff separately; original checkout remains untouched for rollback/provenance.
- Imported tests 4/4, npm audit 0 vulnerabilities, Docker build and Trivy image scan 0 blocking findings, Kustomize render PASS, manifest mutation gate 9/9, and GitOps validator 18/18 with both local source maps.
- Maintained `platform/argocd/applications/legacyapp.yaml` is prepared for the platform repo/path. No Argo sync, cluster mutation, Azure apply, or production deployment was performed.
- Evidence: `docs/adr/015-legacyapp-subtree-import.md` and `docs/evidence/a0-legacyapp-subtree-import.md`.

**Next approval:** review the Argo source-switch diff and approve a controlled shadow/sync validation before retiring the standalone source path.

### A0.1 — Baseline honesty pass: PASS locally (2026-10-20)

Closed three defects that were disclosed but not fixed. No Azure, cluster, or
Argo mutation was performed.

1. **`scripts/bootstrap.sh` could not run.** It applied `gitops/argocd/application.yaml`
   (only present as `.disabled`) and four manifests that `MANIFEST-INVENTORY.md`
   classifies as `LEGACY_NOT_DEPLOYED` / `EXTERNAL_WORKLOAD_REFERENCE` /
   `SUPERSEDED`. Rewritten to: validate every input before touching the cluster,
   apply only `platform/argocd/applications/`, and refuse `legacyapp.yaml`
   unless `APPLY_LEGACYAPP=1` (ADR-015 source switch still unapproved).
2. **`MANIFEST-INVENTORY.md` overstated CI coverage.** `platform/observability/*`
   was marked `RENDERED` although no `kustomization.yaml` existed under
   `platform/`, so pr-gate never rendered it. Relabelled `REFERENCE_NOT_RENDERED`;
   recorded that `dashboards.yaml` and `dashboards/local-platform-dashboard.yaml`
   both define `grafana-dashboard-local-platform`.
   → **Resolved later the same day by F2** (`910cf52`): the duplicate owner
   was removed, **no dashboard was lost**, and gate **G13** now fails if two
   files ever declare the same object again.
3. **`platform/envoy-gateway` gained real kustomize roots** (`gateway/`,
   `proof-backend/`), so its `RENDERED` claim is now produced by pr-gate rather
   than asserted by a document.

Verification (local, 2026-10-20): `bash -n` OK; `validate-gitops.py` 16 passed /
0 failed / 2 not-present; `tests/test_gates.py` 17/17; `policy-gate.py` PASS;
`kubectl kustomize` on all 8 roots rc=0 (new roots: 5 and 2 objects);
kubeconform `-strict` on both new roots → Valid 3, Invalid 0, Errors 0, Skipped 4.
→ **The gate count has grown since:** `tests/test_gates.py` is now **42/42**,
because the F1–F5 regression groups **G11**, **G12** and **G13** were added
after this pass. `validate-gitops.py` is now **16 passed / 0 failed / 2
not-present**, and `policy-gate.py` reports `2 kustomize root(s), 26 object(s)`.

Open item for the next phase: the two `EXTERNAL_REPO_NOT_PRESENT` rows mean
external source trees are still unvalidated in CI. `validate-gitops.py` refuses
a `--repo-map` path outside the repository root, so wiring a real external
checkout is still unsolved.

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
