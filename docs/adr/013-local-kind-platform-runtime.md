# ADR-013 — The portfolio platform runtime is a local kind cluster, not AKS

> **Read this first.** This ADR was written when Azure could not be operated at
> all. It is **superseded in part** by
> [ADR-014 — Azure-first verification](014-azure-first-verification.md), which
> moves verification back onto a real AKS cluster. What survives here is the
> measured quota arithmetic and the role of the kind cluster as the
> **OSS / dry-run profile**. What no longer holds is "kind is where behaviour is
> proven". This file is kept unedited in its reasoning so the decision trail
> stays visible; it was not rewritten to pretend ADR-014 always existed.

- Status: **SUPERSEDED IN PART by [ADR-014](014-azure-first-verification.md)**,
  accepted 2026-09-23, documented 2026-10-02, superseded 2026-10-02. The kind
  cluster remains valid as the **OSS / dry-run profile**, but it is no longer the
  runtime where Kubernetes / AKS / SRE behaviour is verified. Claims below are
  `PRE_AZURE_DRY_RUN` unless ADR-014 states otherwise.
- Supersedes: nothing. It narrows [ADR-012](012-aks-foundation-cost-safe.md),
  which remains valid for the Azure foundation that *was* built.
- Related: `../evidence/local-platform/`, `../../local/kind/README.md`,
  `014-azure-first-verification.md`

## Context

ADR-012 established a cost-safe AKS foundation: one system pool, a temporary
user pool, OIDC + Workload Identity, private ACR pull. It was applied twice
(7A.1, 7A.2) and passed. It then hit a wall that no amount of Terraform could
resolve.

The subscription has a **10 vCPU regional quota**, of which the system pool
already consumes 8. The `StandardDsv6Family` quota is also 10. A quota increase
was filed and `az quota update` returned **`ContactSupport`** — it requires manual
portal/support approval, not a code change. Full detail:
`../evidence/phase7b/quota-7b0-gate.md`.

That leaves a structural conflict:

```text
What the portfolio must demonstrate        What 10 vCPU can hold
──────────────────────────────────────     ─────────────────────────────
system pool            2 × D4s_v6  (8)     already at the limit
user pool + autoscaler  1–2 × D2s_v6 (2–4) exceeds the limit
3-node topology for PDB / drain proofs     3 × D4s_v6 = 12 vCPU, over the limit
a cluster that runs continuously          ≈ $0.55/h ≈ $13/day, forever
```

A second constraint compounds it: the Terraform state backend
(`stflashs3ctfbk01`) is `defaultAction: Deny` behind a fixed IP allowlist on a
residential connection, so `terraform init` fails with 403 whenever the IP
rotates. That is not a portfolio problem to engineer around; it is an
environment property.

The result was that the platform could be **designed** on Azure but not
**operated** there. For a portfolio whose value is *demonstrated* behaviour, an
unrunnable cluster is worth far less than a runnable one on weaker hardware.

## Decision

**Run the portfolio platform on a local 3-node kind cluster. Keep AKS as the
production target architecture, documented and Terraform-managed, but not as the
place where behaviour is proven.**

```text
┌──────────────────────────────┬────────────────────────────────────┐
│ LOCAL (kind) — the runtime   │ AZURE (AKS) — the target           │
├──────────────────────────────┼────────────────────────────────────┤
│ every behaviour is proven    │ Terraform owns the foundation       │
│ 3 nodes, 1.36.1, pinned      │ OIDC, WI, AcrPull, remote backend  │
│ Gateway API + Envoy Gateway  │ 2 × D4s_v6 system pool (real apply)│
│ Argo CD v3.5.3 as authority  │ stopped after evidence capture      │
│ Prometheus + Grafana         │ blocked on quota for a user pool    │
│ ~5.27 GiB of a 7.75 GiB cap  │ ≈ $0.55/h if left running           │
└──────────────────────────────┴────────────────────────────────────┘
```

Concretely:

1. `local/kind/` owns the runtime. `kindest/node:v1.36.1` is **pinned**, not
   `latest`, and was verified present in the registry before being written down.
2. The AKS manifest target stays on the same Kubernetes minor line, so local
   evidence transfers to the Azure target rather than describing a different
   platform.
3. The Azure foundation is **not** deleted. It stays in Terraform, stopped, and
   is re-proven by a transient apply/destroy cycle when quota allows.
4. North-south is **Gateway API + Envoy Gateway**, not ingress-nginx, which is
   retired upstream (March 2026).

## Why not the alternatives

| Alternative | Why rejected |
|---|---|
| Raise the quota and stay on AKS only | `ContactSupport`: needs a human, an unknown wait, and a project that cannot be blocked on an external queue. Revisit if the quota lands. |
| Shrink to fit: 1 system node + 1 user node | A 1-node system pool hides exactly the scheduling, PDB and drain behaviour the portfolio exists to demonstrate. A single node also cannot show that a pod survives node loss. |
| Stop the cluster between demos and keep the quota | Still 8 vCPU blocked whenever anything is running, and it leaves residual ACR Standard + storage + public-IP charges. Saved compute, lost reproducibility. |
| Managed AKS / Azure Local | Reintroduces the quota dependency and a cost profile the portfolio is meant to avoid. |
| Docker Compose / plain containers | No scheduler, no controller, no PDB, no GitOps controller. Nothing in the SRE story survives. |

## Consequences

**Gained**

- Every claim in `docs/EVIDENCE.md` is reproducible on demand, at zero marginal
  cost, in under five minutes (`./scripts/demo-local-platform.sh`).
- A real 3-node topology, so PDB, drain, topology and scheduling behaviour are
  genuinely exercised rather than described.
- No external dependency blocks the work. The quota and the backend firewall
  become Azure-side issues that gate Azure-side proofs, not the whole project.

**Given up — stated plainly, never to be papered over**

- **NetworkPolicy is not enforced locally.** kindnet CNI does not enforce it, so
  this capability cannot be claimed as tested until a policy-enforcing CNI
  (Calico/Cilium) is added or the proof runs on AKS.
- No cloud-managed data tier, no managed Prometheus/Grafana, no Key Vault, no
  real Workload Identity at runtime. The Azure wiring is proven in Terraform and
  in the 7A evidence, not by a running pod fetching a secret.
- No LoadBalancer IP, no HA control plane, no real multi-zone spread.
- Local success is **not** evidence of AKS success. It is evidence that the
  manifests and the operating model are correct on the same Kubernetes version.

## The binding constraint, recorded

The Docker Desktop VM is capped at **7.75 GiB** while the host has 16 GiB. The
L0–L10 stack measures **5.27 GiB**, leaving ≈ 2.48 GiB. Raising the cap is a
manual GUI step that macOS protects from the terminal, so scripts only warn.
Scaling beyond 3 nodes requires that manual step **first**. See
`../../local/kind/README.md` §4.

## Revisit when

- The vCPU quota increase is granted → re-prove the AKS user pool and Cluster
  Autoscaler on a transient apply/destroy cycle.
- A policy-enforcing CNI is added to kind → the NetworkPolicy claim becomes
  locally testable and this ADR's main limitation is lifted.
- CI is available → the local cluster becomes a job runner rather than a
  workstation ritual, which is what makes it durable.

