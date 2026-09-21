# Phase 7A.2 — Focus Plan (2026-09-21)

> Timestamped plan under `plans/` (repo-harness `run new-plan` helper is
> interactive-only; this file is the equivalent artifact).
> `.ai/harness/handoff/resume.md`: absent — `tasks/current.md` is authority.

## 1. Goal

Close Phase 7A completely: freeze 7A.1 PASS as an immutable checkpoint, then
execute **7A.2 — temporary user pool + private ACR pull + Entra Workload
Identity runtime proof**, ending with full cleanup + stopped cluster. STOP
after final report; do NOT implement 7B.

## 2. Verified baseline (7A.1 PASS, committed evidence pending)

- Cluster `aks-portfolio-dev` / RG `rg-aks-platform-dev` / eastasia / **1.36.4**,
  Free tier, currently **Stopped**.
- System pool `sys`: 2× `Standard_D4s_v6`, Regular, autoscaling OFF,
  CriticalAddonsOnly. 2/2 nodes were Ready; kube-system healthy.
- OIDC issuer enabled + `securityProfile.workloadIdentity.enabled = true`
  (foundation only — no pod proof yet).
- Kubelet identity has Terraform-managed **AcrPull** on `acrflashsalep6`
  (classic LegacyRegistryPermissions, admin disabled).
- Stopped-state quota reads `0/10` (deallocated); Running footprint is 8/10
  regional + 8/10 Dsv6 (see `docs/evidence/phase7a/system-foundation-PASS.md`
  correction note).
- Prior DASv5 failure kept as family-quota evidence (`apply-2026-09-21-BLOCKED.md`).
- Key identity distinction for evidence: **private ACR pull = kubelet identity
  + AcrPull** (NOT Workload Identity); **WI proof = SA JWT → OIDC → Entra
  federation → temp UAMI → `az acr show` Reader read** (no Key Vault/Service
  Bus/Storage needed — Azure CLI `--federated-token` suffices).

## 3. Work

### A. Freeze 7A.1 (local, no cloud changes)

1. Fix stale `tasks/current.md` Next line (pre-apply flow) to post-PASS reality.
2. Review intended set only: `docs/evidence/phase7a/system-foundation-PASS.md`
   (untracked), `tasks/current.md`, `plans/2026-09-21-master-roadmap-7a-to-13.md`
   (rev.2), `plans/2026-09-21-microservices-…md`, related Phase 7A plan/status
   docs. Exclude P01/P02 WIP, `*.tfplan`, `plan.json/out`, `.terraform/`,
   `.local/`, tfstate. Secret-scan before commit. Commit, record SHA.

### B. Execute 7A.2 (live, ≈$0.693/h proof window, keep short)

Steps 1–19 per user directive: start → fresh quota gate (regional ≥2 free,
Dsv6 ≥2 free, D2s_v6 `Restrictions==[]`, else STOP, no auto-SKU-switch) →
re-verify OIDC live → temp `work` pool (1× D2s_v6, User, no autoscaler/Spot)
via saved plan (+1 resource, destroy 0) → pool health (2 sys + 1 user, ~10/10,
no other changes in zero-headroom window) → placement proof pod in
`phase7a-proof` pinned by actual node labels → private pull of immutable
`legacy-app:<verified-SHA>` (no secret/admin/latest; capture digest/imageID) →
WI infra via `enable_wi_proof` (temp UAMI + FIC issuer/subject/audience +
Reader on ACR only) → SA `wi-proof` (client-id annotation) → WI pod (label
`azure.workload.identity/use: "true"`, pinned to work; verify env, never print
token) → federated `az login` → `az acr show` read-only → optional
Reader-only negative check (no destructive writes) → capture WI evidence →
delete namespace → destroy WI resources (`enable_wi_proof=false`, destroy
strictly limited) → destroy user pool (`enable_workload_pool=false`, destroy
only `…node_pool.work`, quota back ≈8/10) → `az aks stop` (Stopped; do NOT
claim zero cost) → sanitized evidence docs → FINAL REPORT → STOP.

## 4. Verification

- 19-gate Phase 7A FINAL ACCEPTANCE GATE (directive): all runtime-executed,
  none config-inferred; private-pull ≠ WI stated separately in both proofs.
- Preconditions to re-check live before writing new TF: `enable_workload_pool`
  mechanism exists; `enable_wi_proof` exists or must be added (code change +
  `validate`/`fmt` green before plan).
- `legacy-app:<SHA>` must be the previously verified immutable P02 release —
  resolve SHA from ACR/repo before Step 7, never `latest`.
- Evidence hygiene: subscription/tenant/client IDs redacted unless policy
  permits with reason; no tokens in logs; raw plans gitignored.

## 5. Acceptance criteria

- PASS only if all 19 gates green + 4 evidence files
  (`user-pool-placement`, `private-acr-pull`, `workload-identity-runtime`,
  `phase7a-FINAL-PASS`) + namespace/UAMI/FIC/role/pool deleted + quota ≈8/10
  + cluster Stopped. Any gate red → FAIL/BLOCKED with reason, cleanup still
  executed (never leave pool/nodes running).
- Truthful-claims section lists NOT-claimed items (no ingress/Argo/P01/P02/
  Prometheus/microservices/Kafka/Saga).
- Next recommendation (not implemented): 7B platform bootstrap.

## 6. Risks / rollback

- Zero vCPU headroom during proof window → shortest window, no extra ops.
- OIDC propagation flakiness seen before → live re-verify (Step 3), use actual
  issuer URL, never copy.
- Rollback per step: saved-plan-gated applies; destroy plans strictly scoped;
  freeze commit is docs-only and independently revertible.
