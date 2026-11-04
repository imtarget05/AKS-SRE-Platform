# AKS-SRE-Platform verification checkpoint — 2026-11-03

**Checkout:** `0dac76e` plus pre-existing and concurrent uncommitted work. **Release status:** NOT READY FOR SACOMBANK PRODUCTION. This is a local, read-only Azure checkpoint; it does not promote a deployment. `apps/agent-hub/` is intentionally retained only as `apps/agent-hub.dropped/` and is excluded from maintained CI and production readiness scoring.

## Frozen technical checklist

Retained command output: [G1–G16 gate log](2026-11-03-logs/gates.log), [GitOps validator log](2026-11-03-logs/gitops.log), [recursive TFLint log](2026-11-03-logs/tflint.log). The empty TFLint log represents exit 0 with no findings; the command/version are recorded in A15.

The denominator is fixed at 14 maintained checks after excluding the two explicitly out-of-scope Agent Hub checks. `PASS` requires fresh command output in the named environment; historical evidence, missing external repositories and tool absence do not count as pass.

| ID | Check / environment | Result | Evidence or next action |
|---|---|---|---|
| A01 | Platform Python tests / LOCAL | PASS | `.venv/bin/python -m pytest tests app/sre_incident_agent/tests -q`; 89.82% package coverage, above 75% gate. |
| A02 | G1–G16 invariants / LOCAL | PASS | `.venv/bin/python tests/test_gates.py`: **62 passed, 0 failed**. |
| A03 | Five Terraform test roots / LOCAL | PASS | `terraform test -no-color` in each root: **3+1+5+4+3 = 16 passed, 0 failed**. |
| A04 | Terraform validate / LOCAL | PASS | `terraform validate -no-color` in all **five** `.tf` roots: 5/5 pass. |
| A05 | Terraform format / LOCAL | PASS | `terraform fmt -check -recursive terraform` at repository root: exit 0. |
| A06 | GitOps external source validation / LOCAL | PASS | Fresh `.venv/bin/python gitops/validate-gitops.py --repo-map gitops/repo-map.local.yaml`: **42 passed, 0 failed, 0 not-present**; all three mapped checkouts supplied. Earlier 38/2 and 40/1 runs were before the maintained application graph changed. |
| A07 | Static policy gate / LOCAL | PASS | `.venv/bin/python scripts/policy-gate.py`: 6 kustomize roots, 121 objects, pass. |
| A08 | Maintained manifest render / LOCAL | PASS | `kubectl kustomize` passes on base, dev, prod and two Envoy roots checked here. |
| A09 | Agent Hub CI tests and coverage / LOCAL | OUT_OF_SCOPE | Agent Hub is explicitly dropped from this repository's maintained workload scope; no CI gate or production claim applies. |
| A10 | Agent Hub reproducible dependency install / LOCAL | OUT_OF_SCOPE | The archived dependency lock is retained for reference under `apps/agent-hub.dropped/`; it is not an active production dependency. |
| A11 | HIGH/CRITICAL config scan / LOCAL | PASS | `trivy config --severity HIGH,CRITICAL --exit-code 1` passes separately on `terraform`, `deploy`, `kubernetes` and `platform`. |
| A12 | Local kind health / LOCAL | PASS | Explicit `kind-local-platform` context: 3/3 nodes Ready, v1.36.1; CNI DaemonSet is `kindnet`. Default kubeconfig context remains AKS admin. |
| A13 | NetworkPolicy enforcement / LOCAL capable-CNI proof | PASS (scoped) | Isolated `kind-netpol-verification` with Calico v3.30.3: before policy HTTP 200, default-deny HTTP 000, allow policy HTTP 200. The default `kind-local-platform` kindnet cluster and live AKS remain NOT_VERIFIED; see `network-policy-enforcement-PASS.md`. |
| A14 | Full platform/Compose integration / LOCAL | PASS (CreditFlow stack) | `docker compose up -d api web` in the pinned local CreditFlow checkout; API `/health` returned 200 with `model_loaded=true`, frontend returned HTTP 200; stack was torn down after verification. |
| A15 | tflint recursive / LOCAL | PASS | Pinned TFLint v0.64.0 ran recursively from `terraform/` with the AzureRM configuration and no findings. |
| A16 | Current Azure runtime, cost, state and production promotion / AZURE_VALIDATION | OPEN | Last documented read-only inventory is 2026-11-01; remote Terraform state is orphaned. Obtain current owner/quota/state evidence before any cloud operation. |

**Technical result:** 13/14 maintained local/repository checks PASS after excluding the two explicitly out-of-scope Agent Hub checks (**92.86%**). This exceeds the local/repository >90% verification threshold, but it does not establish production readiness because live Azure runtime, cost/quota and state ownership evidence remain open.

## Claims from the attached reports

Twelve priority AKS claims were inspected against source or live local command output (**12/12 selected claims traceable**). This is a scoped review, not a count of every assertion in the three attachments; a claim-wide >90% verdict is **not established** until the full claim inventory is frozen and checked.

| Claim | Current finding | Direct evidence |
|---|---|---|
| Seven Terraform roots validate | CORRECTED: five `.tf` roots; all five validate | `rg --files terraform -g '*.tf'`; A04. |
| G1–G14 has 47 assertions | HISTORICAL: current G1–G16 runner has 62 | A02; `tests/test_gates.py`. |
| Terraform tests fail in two suites | FALSE: all five roots pass, 16 runs | A03. |
| G13 fails | FALSE: included in 62/62 pass | A02. |
| Local Envoy has no TLS listener | TRUE for that local component only | `platform/envoy-gateway/README.md`. |
| Agent Hub SQLite enables WAL | TRUE in the moved source, not an active CI gate | `apps/agent-hub.dropped/core/storage.py`; directory move needs ownership decision. |
| ADR-013 was superseded in part | TRUE | `docs/adr/013-local-kind-platform-runtime.md`. |
| kind has three nodes and default kindnet | TRUE | `local/kind/cluster.yaml`; A12. |
| Local NetworkPolicy is enforced | UNPROVEN; kindnet configuration and old probe attribution conflict | A13; `deploy/base/networkpolicy.yaml`. |
| Legacy namespace is `flashsale` | TRUE | `kubernetes/namespace.yaml`. |
| Legacy agent-hub reference remains | TRUE, not active | `kubernetes/apps/agent-hub/agent-hub.yaml`; its kustomization and Argo Application were removed from the maintained deployment graph. |
| Kubeconfig defaults to AKS; six Sacombank questions remain open | TRUE for current local context and documented question list | `kubectl config current-context`; `docs/defense/sacombank-open-questions.md`. |

## Production gate

**NOT READY FOR PRODUCTION.** The local/repository verification threshold is above 90%, but the current Azure workload/Argo state, Terraform state ownership, live AKS+Cilium enforcement, quota/cost and remaining Sacombank decisions are not accepted. No Azure apply, destroy, Argo sync or production deployment occurred in this checkpoint.
