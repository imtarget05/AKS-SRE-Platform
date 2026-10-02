# Phase 0 Audit — AKS-SRE-Platform (read-only)

- **Date:** 2026-10-02
- **Scope:** repository state only. No code file was modified by the audit, no
  Azure resource was read for mutation, no cluster was applied or destroyed.
- **Method:** `git fetch --prune` / `status` / `branch -a` / `worktree list` /
  `log`, full `find`, content read of every decision file, `terraform fmt -check
  -recursive`, `gitops/validate-gitops.py`, and a toolchain inventory.

## 1. Repository state (measured)

| Item | Value |
|---|---|
| Remote | `https://github.com/imtarget05/AKS-SRE-Platform.git` |
| Branches | `main` only (no feature branches, no stale remotes after prune) |
| HEAD | `0cbb7b1` — `docs: correct four factually false README claims` |
| Working tree | **clean** (no modified, no untracked) |
| Worktrees | 1 (the main checkout) |
| Tracked files | 90 |
| Repo size | 768 KiB |
| `terraform fmt -check -recursive` | **clean** (exit 0) |
| `terraform/aks-foundation/.terraform` | absent — root is **not initialized** locally |
| `gitops/validate-gitops.py` | **FAIL (2)** — cannot map `FlashSale-Backend` / `Productionized-LegacyApp` to local checkouts |

## 2. Toolchain (measured on this host)

| Tool | Status |
|---|---|
| terraform | **v1.16.3** installed |
| kubectl | **v1.36.1** installed |
| kind | **v0.33.0** installed |
| helm | **v4.3.0** installed |
| docker | installed; `desktop-linux`, 8 CPU, `MemTotal` 8 321 798 144 B (7.75 GiB) |
| az | installed, logged in (`Azure subscription 1`) |
| trivy | **0.74.0** installed |
| tflint | **NOT installed** |
| tofu | NOT installed |
| syft | NOT installed |
| cosign | NOT installed |
| k6 | NOT installed |

## 3. Contexts present on this host

| Context | State |
|---|---|
| `aks-portfolio-dev` | credentials present, but the cluster is **Stopped** (VMSS capacity 0) per `docs/evidence/azure-teardown/pre-destroy-inventory.md` |
| `kind-local-platform` | credentials present, cluster not running in this session (current context is `docker-desktop`) |

## 4. What already exists, and its real quality

The repository is **not** a tutorial skeleton. It contains a verified local
platform (L0–L11) built on kind, and a partially verified Azure AKS foundation
(Phase 7A, applied once, then stopped).

### 4.1 Real, reusable, high value

| Area | Evidence | Verdict |
|---|---|---|
| kind 3-node cluster, pinned `kindest/node:v1.36.1`, measured RAM budget | `local/kind/`, commit `991ec05` | **KEEP** — reusable as the CI/dev runtime |
| Argo CD v3.5.3 non-HA + `AppProject/portfolio` with a real namespace allowlist | `platform/argocd/`, `docs/evidence/local-platform/l4-argocd-PASS.md` | **KEEP** — the GitOps authority already exists |
| GitOps forward deploy + **rollback by `git revert`** proven on two repos | `docs/evidence/local-platform/l9-gitops-PASS.md` | **KEEP** — this is the drift/rollback story |
| Gateway API + Envoy Gateway v1.9.1 shared north-south, hostname routing | `docs/evidence/local-platform/l8-shared-gateway-PASS.md` | **KEEP** — ingress-nginx correctly retired |
| Prometheus + Grafana 91.5.0, 14 scrape jobs, 3 Git-provisioned dashboards, one **fired-and-resolved** PrometheusRule | `docs/evidence/local-platform/l10-observability-PASS.md` | **KEEP** — extend, do not rebuild |
| Terraform AKS foundation: OIDC issuer, workload identity, AcrPull via kubelet identity, remote azurerm backend | `terraform/aks-foundation/`, `docs/evidence/phase7a/phase7a-FINAL-PASS.md` | **KEEP, restructure** (see §5) |
| Workload Identity FIC wiring (gated, destroyed same session) | `terraform/aks-foundation/wi-proof.tf` | **KEEP** as the reference pattern |
| Claim-discipline culture: explicit non-claims, measured numbers, no fabricated metrics | `docs/EVIDENCE.md`, `tasks/current.md`, `AGENTS.md` | **KEEP** — the repo's strongest asset; the new plan must not weaken it |

### 4.2 Terraform-specific gaps

| Gap | Measured fact |
|---|---|
| No `backend.tf` | backend block is **inline in `versions.tf`**, hardcoding `rg-flashsale-tfstate` / `stflashs3ctfbk01` — an out-of-repo dependency on another repo's resource group |
| No `modules/` | single flat root, no reusable `network` / `aks` / `acr` / `keyvault` / `identity` / `monitoring` module |
| No `environments/` | no `dev` / `validation` / `prod` split; environment identity is a handful of `default` values |
| **No `terraform test` at all** | zero `*.tftest.hcl` files exist in the repo |
| No `tflint` config | tflint is not even installed |
| User pool is a temporary hack | gated by `enable_workload_pool` (default `false`) purely to dodge quota; `main.tf:36` explicitly defers zones to "Phase 10" |
| `node_provisioning_profile { mode = "Manual" }` | Cluster Autoscaler cannot be demonstrated in this shape |
| Node autoscaling | `auto_scaling_enabled = false` on both pools, by cost rule |
| `.terraform` absent | the root has not been initialized on this host, so `validate` has not been re-run recently |

### 4.3 Kubernetes-manifest gaps

Measured by pattern search over `kubernetes/`, `gitops/`, `platform/`:

| Capability the target plan requires | Present in this repo? |
|---|---|
| `kind: HorizontalPodAutoscaler` | **NO — zero HPA manifests anywhere** (only a KEDA `ScaledObject`) |
| `kind: NetworkPolicy` | **NO** |
| `livenessProbe` / `startupProbe` | **NO** (only a `readinessProbe` in the Envoy proof-backend, which is demo scaffolding) |
| `topologySpreadConstraints`, `podAntiAffinity` | **NO** |
| `securityContext` in `kubernetes/` | **NO** (the real hardening lives in the P01/P02 repos' overlays) |
| `PodSecurity` admission | **NO** |
| immutable digest pinning | **NO** — `kubernetes/order-worker.yaml:22` uses `:latest` and a placeholder ACR host |
| `kind: PodDisruptionBudget` | yes, but it selects `app: order-api`, and **no `order-api` manifest exists in this repo** → the PDB selects nothing |

Two internal inconsistencies already recorded in the README, confirmed still true:

- `kubernetes/order-worker.yaml:29-33` injects a **Service Bus** connection string
  while `kubernetes/keda-autoscaler.yaml` watches **RabbitMQ** `QueueLength`.
- `kubernetes/keda-trigger-auth.yaml` references a secret created out-of-band;
  `scripts/bootstrap.sh:38` applies `gitops/argocd/application.yaml`, which exists
  only as `.disabled`.

### 4.4 Delivery gaps

| Capability | Present? |
|---|---|
| `.github/` | **absent entirely** — no CI, no OIDC workflow, no image build, no Trivy gate |
| `app/` (the `sre-demo-api` workload) | **absent** |
| `tests/` | **absent** |
| `runbooks/`, `alerts/`, top-level `dashboards/` | **absent** (dashboards live under `platform/observability/dashboards/`) |
| `scripts/load/`, `scripts/chaos/`, `scripts/evidence/` | **absent** |
| `sre-demo-api` image / Dockerfile | **absent** — this repo owns no image; it consumes P01/P02 |

### 4.5 Documentation gaps

- `tasks/current.md` is an append-only history with **six** sections all titled
  `ACTIVE GOAL`; the newest wins. Currently accurate, degrades with every phase.
- `docs/adr/012-aks-foundation-cost-safe.md` is **structurally corrupted**: lines
  27-70 contain a half-written decision, then a nested `## Architecture` heading
  inside a code fence, then an orphaned second ASCII tree (lines 65-70) after the
  fence closed. The `rg-aks-platform-prod` name inside the fence is also
  contradicted by `rg-aks-platform-dev` on line 6.
- `docs/adr/012` status line still says `PROPOSED (v2) — NOT APPLIED`, which is
  **false**: Phase 7A.1 and 7A.2 both applied and passed on 2026-09-21.
- No ADR exists for the local-platform decision (kind as the portfolio runtime) —
  currently the single most consequential architectural decision here.
- All relative markdown links resolve; no broken links found.

| `docker-desktop` | current context |


## 5. KEEP / UPGRADE / REMOVE / MISSING

### KEEP (do not touch)
- `local/kind/*` — the runtime that makes everything else testable at zero cost
- `platform/argocd/*`, `gitops/projects/portfolio.yaml` — working GitOps authority
- `platform/envoy-gateway/*` — correct modern north-south
- `platform/observability/*` — working Prometheus/Grafana/alert
- `terraform/aks-foundation/wi-proof.tf` — the workload-identity reference pattern
- `docs/evidence/**`, `docs/EVIDENCE.md`, `AGENTS.md`, `plans/**` — evidence discipline
- `terraform/legacy/main.tf.disabled` — historical only, credentials already purged

### UPGRADE (restructure in place, preserve behaviour)
- `terraform/aks-foundation` → `terraform/{modules,environments}` layout; extract
  the inline backend into `backend.tf` with no hardcoded cross-repo RG; replace
  the `enable_workload_pool` hack with a real user pool; enable node autoscaling.
- `kubernetes/` → a real `deploy/base` + `overlays/{local,validation,prod}` tree
  owned by this repo, around a workload this repo owns.
- `tasks/current.md` → one live section, history moved to `plans/`.
- `docs/adr/012` → repair the corruption and correct the status.
- `README.md` → reconcile with the target architecture.

### REMOVE / SUPERSEDE
- `kubernetes/order-worker.yaml` + `keda-autoscaler.yaml` + `keda-trigger-auth.yaml`:
  the Service-Bus-vs-RabbitMQ halves disagree, the PDB they reference matches
  nothing here, and the KEDA trigger is explicitly out of 7A scope. These are P01
  concerns. **Supersede** with a scaled object against a workload this repo owns;
  do not keep two contradictory halves.
- `gitops/argocd/application.yaml.disabled` and the `bootstrap.sh` step referencing
  it — a bootstrap script that cannot run its own step 5/5.
- `terraform/data-protection` (pointer note only) and the
  `FlashSale-Backend` / `Productionized-LegacyApp` `sourceRepos` coupling in
  `AppProject/portfolio` — that coupling is what makes
  `gitops/validate-gitops.py` fail.

### MISSING (must be built)
1. `.github/workflows/` — PR gate; OIDC-to-Entra Azure verify with a **negative
   control**; image build + Trivy + SBOM + digest pinning
2. `app/sre-demo-api` — a real workload owned by this repo
3. `terraform test` + `tflint` + semantic plan invariants
4. HPA (none exists), NetworkPolicy (none), probes, topology spread, PodSecurity
5. Key Vault + workload-identity-to-Key-Vault negative control
6. Load/chaos/evidence scripts, runbooks, SLO + error-budget definitions
7. Azure transient validation profile (bootstrap → proof → destroy)

## 6. Hard blockers found during the audit

1. **Azure quota.** Phase 7B is blocked on a manual subscription vCPU increase
   (`StandardDsv6Family` 0/10 after the system pool; `az quota update` returned
   `ContactSupport`). A user pool + cluster-autoscaler demonstration therefore
   **cannot** be done on Azure today. State this as a gate; do not work around it
   silently.
2. **Terraform backend is not reachable.** Both tfstate storage accounts are
   `defaultAction: Deny` with a fixed IP allowlist, so `terraform init` fails 403
   from a rotated residential IP. Any Phase 1 work against the real backend is
   blocked until the allowlist is fixed or a private endpoint is used.
3. **`gitops/validate-gitops.py` fails** because it resolves two external repos to
   local paths that do not exist. A CI gate built on it is red on day one.
4. **No CI exists**, so every claim in this repo is currently manual-only. The
   single highest-value change is the CI gate, not more manifests.

## 7. Recommended first three moves

1. **Repair the honesty layer first** — ADR-012 corruption, false status line,
   `tasks/current.md` single live section, new ADR-013 for the kind decision.
   Cheap, and it protects every later claim.
2. **Stand up `.github/workflows/`** — fmt/validate/test/tflint gate, manifest
   render gate, and the OIDC positive/negative control. This converts existing
   manual evidence into enforced evidence.
3. **Then restructure Terraform** into modules + environments and add
   `terraform test` invariants, without changing what the existing root produces.

Deliberately not first: HPA, Prometheus polish, and any Azure apply — all three
are either blocked (quota, backend firewall) or better done once CI can prove
them.

## 8. What this audit did not do

- Did not run `terraform init`, `plan` or `apply` (root not initialized; backend
  firewall known-blocked).
- Did not start the AKS cluster or the kind cluster.
- Did not create, modify or delete any existing file in the repository. The only
  file added is this audit document.
- Did not query Azure beyond the locally cached `az account show` context.

---

## Addendum — 2026-10-02, later the same day: §6.1 and §6.2 are superseded

The audit above did **not** query Azure, so §6.1 (quota) and §6.2 (state backend)
were carried forward from September evidence. Both were re-measured later on
2026-10-02 and **both were wrong**:

```text
§6.1 "10 vCPU quota exhausted, ContactSupport"
    → az vm list-usage: Total Regional vCPUs 0/10 in eastus AND eastasia.
      The 7A cluster was destroyed after evidence capture and released its
      nodes. ADR-013 mistook a transient "currently consumed" for a
      structural ceiling. No quota increase is required.

§6.2 "both tfstate accounts Deny behind a fixed IP allowlist → 403"
    → az group list returns only NetworkWatcherRG, rg-portfolio-evidence,
      rg-maia-tfstate, rg-maia-verify.
      `stflashs3ctfbk01` / `flashsale-prod-rg` do not exist in this
      subscription. The only storage account, sttfmaia, belongs to MAIA and
      has defaultAction: Allow with zero IP rules.
      There is no firewall to bypass and no state to inherit.

§6.4 "no CI exists, so the single highest-value change is CI"  → STILL TRUE.
§6.3 "validate-gitops.py fails"                                → STILL TRUE.
```

The capacity ceiling of 10 vCPU is real and still governs the design, but it is
a ceiling to design within, not an exhausted quota to wait on. The architecture
consequences are recorded in
[`../adr/014-azure-first-verification.md`](../adr/014-azure-first-verification.md).

This addendum is deliberately appended rather than folded in: the audit is a
dated record of what was known when it was written, and rewriting it would hide
the fact that the September conclusions were based on unmeasured assumptions.
