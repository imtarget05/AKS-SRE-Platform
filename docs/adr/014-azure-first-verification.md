# ADR-014 — Azure-first verification: AKS is the runtime, kind is the OSS profile

- Status: **ACCEPTED (2026-10-02).** Active. Execution Wave 1 = Phase A+B+C.
- Supersedes: **ADR-013 in part.** [ADR-013](013-local-kind-platform-runtime.md)
  remains valid for its measured quota arithmetic and for the role of the kind
  cluster as the OSS / dry-run profile. What no longer holds is "kind is the
  runtime where behaviour is proven".
- Extends: [ADR-012](012-aks-foundation-cost-safe.md) (the Azure foundation that
  was built and applied on 2026-09-21),
  [ADR-013](013-local-kind-platform-runtime.md).
- Related: `../audit/2026-10-02-phase0-repository-audit.md`,
  `../engineering/CURRENT_STATE.md`, `../evidence/phase7a/`

## Context

ADR-013 was written on 2026-09-23, one day after Phase 7A, on the belief that
Azure was permanently unusable. Three things were measured on **2026-10-02**
that make that belief no longer true.

**1. The quota is not exhausted. It is empty.** ADR-013 recorded
`StandardDsv6Family 0/10` and `az quota update` → `ContactSupport`, and treated
that as a wall. Measured again, after the 7A teardown released its nodes:

```text
$ az vm list-usage --location eastus
Total Regional vCPUs          0 / 10
Standard Dsv6 Family vCPUs    0 / 10
Standard Dsv5 Family vCPUs    0 / 10
Standard Ddsv6 Family vCPUs    0 / 10
$ az vm list-usage --location eastasia   → identical, 0 / 10
```

The blocker was never "10 vCPU is too small". It was "10 vCPU is already
consumed", which was true only while a cluster ran. ADR-013 misread a transient
state as a structural limit. No quota increase is required to proceed.

**2. The remote-state backend no longer exists.** ADR-013 recorded a `403` on
`terraform init` from a `defaultAction: Deny` storage account behind a
residential IP allowlist. Measured:

```text
$ az group list
NetworkWatcherRG  rg-portfolio-evidence  rg-maia-tfstate  rg-maia-verify

$ az storage account show -n stflashs3ctfbk01 -g flashsale-prod-rg
ERROR (ResourceGroupNotFound)
```

`stflashs3ctfbk01` and `flashsale-prod-rg` are absent from this subscription. The

## Decision

**Verify on a real AKS cluster. The workstation is an authoring surface, not a
cluster host.**

```text
┌───────────────────────────────┬──────────────────────────────────┐
│ AZURE AKS — the proof surface │ LOCAL kind — the OSS profile     │
├───────────────────────────────┼──────────────────────────────────┤
│ Managed Prometheus + Grafana  │ Prometheus + Grafana + ELK       │
│ Application Insights / Logs   │ Logstash → ES → Kibana          │
│ Cilium enforces NetworkPolicy │ kindnet: NetPol NOT enforced     │
│ HPA + AKS Cluster Autoscaler  │ no autoscaling proof             │
│ Workload Identity → Key Vault │ no Key Vault                     │
│ Terraform apply in CI        │ ./scripts/demo-local-platform.sh │
│ ~$0.55/h, destroyed after    │ free, ~5.27 GiB RAM              │
└───────────────────────────────┴──────────────────────────────────┘
```

Rules that follow, and that later phases must not drift from:

1. **A claim is labelled by where it ran.** `docs/EVIDENCE.md` gains an
   `Environment` column. Local-kind results are `PRE_AZURE_DRY_RUN`. A local
   result is never relabelled as Azure evidence.
2. **One log sink per profile.** Azure overlay routes Fluent Bit → Log
   Analytics. OSS overlay routes Fluent Bit → Logstash → Elasticsearch →
   Kibana. Never both, to avoid duplicate ingestion, duplicate billing, schema
   divergence and ambiguous correlation. Correlation is created by the
   application injecting `trace_id`/`span_id` into its structured log **before**
   shipping; the sink does not invent correlation semantics.
3. **ELK is `IMPLEMENTED_TESTED_LOCAL` / `NOT_APPLIED_ON_AKS_QUOTA`.** Not
   unfinished work — a measured capacity decision. A 2 GiB Elasticsearch heap
   needs ≈4 GB RSS ≈2 vCPU, plus Kibana and Logstash. The validation envelope
   leaves ≈2 vCPU after the node pools, and that budget is already owed to
   Prometheus, the OTel Collector and a synthetic prober. Forcing Elasticsearch
   into an undersized pod would produce a red, unhealthy stack that proves
   nothing. Revisit if quota is raised.
4. **SLO targets are `PROPOSED` until a baseline is measured.** The lifecycle is
   `PROPOSED → BASELINE_MEASURED → TARGET_JUSTIFIED → DEFINED_AND_TESTED`.
   Availability 99.9%, p95 < 500 ms, 5xx < 1%, recovery < 120 s are starting
   hypotheses, not commitments. Thresholds are chosen *from* the Azure baseline.
5. **Burn-rate alerts use error-budget semantics**, never a bare error rate:
   `burn_rate = observed_error_ratio / (1 - SLO)`, evaluated as a short/long
   window pair — fast `5m + 1h`, slow `30m + 6h` — with 14.4 / 6 retained only
   while the policy is 99.9%, and only after baseline justifies the policy.

## Why not the alternatives

| Alternative | Why rejected |
|---|---|
| Stay on kind as the proof surface | kindnet does not enforce NetworkPolicy, so the security claim is unreachable locally. The autoscaling story also stays theoretical, since a laptop cluster is not the capacity ceiling an operator actually worries about. This was ADR-013's mistake: it accepted weaker proofs because they were available, rather than because they were sufficient. |
| Ask for quota first, then start | Rejected as sequencing. The quota is not the blocker. Waiting on support for a problem that does not exist is the exact failure ADR-013 already recorded once. |
| Keep AKS, but demonstrate that it is unavailable | An availability failure story is not a portfolio. The interesting claims are the ones that need a real cloud provider: managed identity, Key Vault, real network policy, real node autoscaling. |
| Self-hosted Prometheus + Grafana + ELK everywhere on AKS | Cheaper, and it is the kind profile. On Azure it spends the 2 vCPU of headroom the cluster-autoscaler proof needs, and it is not the Azure baseline an AKS engineer is expected to run. |
| Build the CI runner on the workstation | Reintroduces the laptop as a dependency. Trust, quotas and state must live in Azure and GitHub. |

## Consequences

**Gained**

- Every capability claim in `docs/EVIDENCE.md` gains a real Azure row: Cilium
  enforcing a deny, HPA scaling on real CPU, AKS Cluster Autoscaler adding a real
  VMSS node, a pod's Workload Identity reaching Key Vault, and a burn-rate alert
  that actually fires and resolves.
- Cost stays comparable to 7A (≈ $0.20–$1 per validation cycle) because the
  cluster is transient and the capacity envelope is 8 vCPU, not 10.
- The repo stops depending on a 7.75 GiB Docker VM cap, which is a machine
  property that has no business appearing in an Azure platform's evidence.

**Given up — stated plainly**

- `local/kind/` is demoted to the OSS profile. Its L0–L11 evidence stays valid
  and is not deleted, but it stops being the headline.
- Some capabilities are proven twice: once on kind (OSS profile, ELK) and once
  on AKS (Azure profile, managed services). That duplication is deliberate — it
  is the direct demonstration of the vendor-neutral claim.
- Azure CI requires a real Entra federated identity and an ACR, which is Phase C
  work that must succeed before any apply. There is no offline fallback.
- The quota margin is thin: 2 vCPU. Cluster Autoscaler is proven within it, but
  no second environment may be created in this subscription without a quota
  increase. The other portfolio repos share this ceiling.

## Revisit when

- The regional quota is raised → run ELK on AKS, and widen the autoscaling proof
  from 1→2 nodes to a larger range.
- A private-cluster AKS profile is built for prod → the validation profile's
  public API server must then be justified in writing, never silently inherited.
- Managed Grafana or Application Insights proves too expensive for a portfolio
  → the OSS profile is already the fallback, and the switch must be recorded as
  a cost decision, not a convenience.

6. **Azure capacity is transient.** Validation is applied, proven, and destroyed.
   The cluster is never left running for a portfolio. Cost Safety Mode stays on
   (`../../terraform/README.md`, ADR-012).
7. **The laptop stays clean.** No kind cluster is required for any claim. Build,
   scan and publish happen in GitHub Actions. Nothing in this repo may depend on
   the Docker Desktop memory cap.

only storage account is `sttfmaia` in `rg-maia-tfstate`, which belongs to
**MAIA**, has `defaultAction: Allow` and zero IP rules. So there is no firewall
to bypass and no state to inherit. This repo needs its own state identity, and
the "home IP" design constraint is a constraint on a resource that no longer
exists.

**3. AKS was already proven to work, once.** `docs/evidence/phase7a/` contains a
complete live apply: system pool, temporary user pool, workload placement,
private ACR pull by digest, Workload Identity federated token exchange, and full
teardown. 19 gates, all runtime-executed. Compute cost ≈ $0.20. The foundation
is not theoretical.

What remains genuinely unproven is the long list: HPA, Cluster Autoscaler,
NetworkPolicy enforcement, PodDisruptionBudget, topology spread, health probes,
SLO and burn-rate alerting, failure injection, and continuous CI. Every one of
those is Kubernetes or SRE behaviour, and every one of them can be proven on AKS
today within 8 of the 10 available vCPU.
