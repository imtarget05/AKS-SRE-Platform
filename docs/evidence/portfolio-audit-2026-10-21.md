# AKS/SRE business-to-evidence audit — 2026-10-21

**Code base:** `62c901ff0e399bc028b4a4b3d3fb53a314703975`.
**Method:** read the tracked configuration, current checkpoint, tests and
recorded outputs; rerun local gates. No Azure mutation or fresh Azure runtime
claim was made. The generated `docs-site/site/` working-tree changes predate
this audit and were not touched.

Status vocabulary: **historical Azure validation** = runtime observation on a
cluster since deleted; **local verified** = kind/CLI result; **implemented,
runtime unverified** = configuration/code without the named observation;
**design/demo** = intended or isolated behavior.

| Use case / decision | Status and environment | Commit / reproduce | Observed result | Limit |
|---|---|---|---|---|
| Review an AKS change before cost is incurred → Terraform fmt, validate, test, lint | **Validate rerun locally; remaining controls previously reported in CI** | This HEAD: `terraform -chdir=terraform/aks-foundation validate`; CI source: `../../.github/workflows/pr-gate.yaml`; [Phase B CI](phase-b-ci/README.md) | Validate passed here; offline Terraform tests cover five run blocks across three roots per current task log | Fmt/test/lint were not rerun in this audit; offline validation does not apply Azure resources; current backend is local |
| Reject malformed/unowned GitOps resources → render, inventory, AppProject policy | **Local verified** | This HEAD: `.venv/bin/python tests/test_gates.py`; `scripts/verify-gitops-all.sh` | **47 assertions passed, 0 failed**; full multi-repo validation **18 passed / 0 failed / 0 not-present** via `gitops/repo-map.local.yaml` | External checkout paths mapped locally across monorepos |
| Isolate platform and tenant workloads → system/user node pools | **Historical Azure validation** | [Phase 7A placement evidence](phase7a/user-pool-placement-PASS.md) | Tenant pod placement on user pool, none on system pool | Temporary pool and cluster deleted; no autoscaler scale-out |
| Pull a private image without a stored registry password → kubelet managed identity | **Historical Azure validation** | [ACR proof](phase7a/private-acr-pull-PASS.md) | Digest pull without `imagePullSecret` | Separate from pod Workload Identity; not every workload proved |
| Give one proof pod scoped Azure access → ServiceAccount federation | **Historical Azure validation** | [WI proof](phase7a/workload-identity-runtime-PASS.md) | Token exchange and scoped Azure read, plus negative cleanup control | Not a Key Vault read by application pod; temporary identity deleted |
| Restore declarative state after drift → Argo CD | **Local kind verified** | [Self-heal record](local-platform/2026-10-21-recreate/selfheal-reverification-2026-10-21.md) | Spec drift reconciled in **21 s**; deleted Deployment recreated and ready in **17 s** | No AKS Argo runtime evidence; times are two local observations, not an SLO |
| Route and observe a workload → Gateway API/Envoy, Prometheus/Grafana | **Local kind verified** | [Gateway proof](local-platform/l8-shared-gateway-PASS.md), [alert proof](local-platform/l10-observability-PASS.md) | Multi-namespace route and an alert fire/resolve cycle on kind | No Azure Gateway/observability runtime or 30-day SLO history |
| Prove resilience under scale/network/drain/DR faults | **Local verified** | [NetworkPolicy proof](network-policy-enforcement-PASS.md), [PDB drain proof](pdb-drain-drill-PASS.md), [DR proof](disaster-recovery-drill-PASS.md), [SLI proof](sli-slo-baseline-PASS.md) | 6/6 NetPol probes (packet drop on unauthorized ingress/egress), PDB active drain (100% uptime, 0 dropped requests), DR drill (RTO 0.1581s, RPO 0s), SLI burn rate calibrated | Tested under local 3-node cluster and transient drill DB; Azure-scale runs subject to cost gate |

## Prioritized gaps and remedies

| Priority | Finding / interview risk | Simpler alternative and trade-off | Verification needed |
|---|---|---|---|
| P0 — claim integrity | The generated-site source presented deleted AKS as live, invented a `tests/test_gate_matrix.py` transcript, implied Argo/Prometheus on AKS and advertised unrelated portfolio scan totals. | Keep a short environment-labelled table sourced from actual artifacts; lose a flashy dashboard but gain auditability. | Site source build and search for unsupported claims; compare each table row to primary evidence. |
| P1 — state safety | Terraform backend remains `local`; historical remote backend state is orphaned. Reusing a stale backend could create or destroy the wrong infrastructure. | Do no cloud apply; first reconcile backend/state ownership with a saved reviewed plan. | Independent state inventory, plan diff, owner review before any Azure mutation. |
| P1 — source authority | GitOps validator reports two external source trees as `NOT_PRESENT` without an explicit repo map. The local metadata checks pass, but the source content was not validated in that run. | Keep the not-present label instead of treating 16/0 as whole-system green. | Supply the exact checkout/ref to the validator and render both source trees before a release claim. |
| P1 — network/security proof | Default-deny NetworkPolicy objects were accepted, but a deny/allow traffic test did not finish; classic Azure CNI run did not prove Cilium. | Keep policy as configuration rather than claim enforcement. | Allowed and forbidden traffic probes on an approved Azure profile, with packet/result evidence. |
| P1 — SRE runtime | Autoscaler, PDB/drain, production SLO and DR are unmeasured. | Demonstrate local alert/self-heal today; defer Azure experiment until capacity and cost gate. | Recorded scale event, drain, restore and baseline with environment labels. |
| P2 — workload story | LegacyApp `/sync` is a no-op reference endpoint. | Use it only to show platform contracts; use owning product repo for business workflow. | An actual inventory integration would need a contract, failure cases and E2E. |

## Five-minute local demo: success and failure

From this repository root at the audited HEAD:

```bash
.venv/bin/python tests/test_gates.py
kubectl kustomize platform/envoy-gateway/gateway >/dev/null
(cd apps/legacy-inventory/src && npm test)
```

The gate script itself injects negative cases (missing resource, orphan
manifest, forbidden AppProject destination) and asserts they fail. Show both
the expected negative result and the final **47 passed, 0 failed** summary.
Then open the [kind self-heal record](local-platform/2026-10-21-recreate/selfheal-reverification-2026-10-21.md)
for runtime failure/recovery timestamps, and the
[Azure proof](phase7a/phase7a-FINAL-PASS.md) for a separate historical environment.
No cloud cluster is required for this interview demo.

## Interview decision chain

Business need: changes must be reviewable and recoverable at bounded cost.
Use case: a bad route/policy fails before sync; a legitimate deployment can
recover from drift. Architecture: Terraform owns the cloud boundary; CI checks
render/ownership; Argo owns desired workload state; metrics expose symptoms.
Failure: orphan manifest, disallowed namespace, drift, metric-source outage.
Evidence: negative gate fixtures, kind self-heal and alert records, and a
separate transient Azure identity/placement proof. The proof boundary is part
of the answer, not a footnote.

Across the portfolio, the owning OpsBridge audit records a fresh local
PostgreSQL/RabbitMQ integration run (**39/39**), six concurrency-harness
regressions and one disposable 50/10 run (**10 accepted, 40 rejected, stock 0,
10 persisted orders**). The SmartDocumentChatbot audit records local owner
and direct-route security fixes with a successful **395/395** backend rerun
after one earlier asynchronous timing failure. These are **other repositories'
working-tree results**, not AKS runtime proof or remote CI results; their
remaining compensation and serving-HITL crash windows are tracked in the
owning audits.
