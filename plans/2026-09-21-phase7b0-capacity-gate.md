# Phase 7B.0 — Capacity & Platform Architecture Gate — Focus Plan (2026-09-21)

> Timestamped plan under `plans/` (repo-harness `run new-plan` interactive-only
> equivalent). `.ai/harness/handoff/resume.md`: absent — `tasks/current.md` authority.
> Scope: 7B.0 ONLY. No User pool, no Envoy Gateway, no public Gateway, no Argo CD,
> no P01/P02. STOP after final report; 7B.1 NOT authorized.

## 1. Goal

Gate Phase 7B on (a) durable vCPU headroom (10→16 regional + Dsv6) and (b) a
corrected north-south architecture: **Gateway API + Envoy Gateway**, replacing
the retired ingress-nginx, with future Istio Ambient reserved for east-west.

## 2. Baseline (verified)

- 7A FINAL PASS committed (`c27ec06`); tree clean at plan creation.
- Cluster Stopped (1.36.4); live usage 0/10 + 0/10 while stopped; Running
  footprint 8/10; persistent `work` pool (1×D2s_v6 = 2 vCPU) would pin 10/10
  with zero headroom → increase required BEFORE 7B.1.

## 3. Work

### STEP 1 — Fresh quota (done live at plan time)

Regional `cores` 0/10, `StandardDsv6Family` 0/10 (stopped), D2s_v6
`Restrictions=[]`. Running math: 8 + 2 = 10/10 → confirms gate.

### STEP 2 — Quota request 10→16 (EXECUTED 2026-09-21 → API FAILED, manual path)

- `Microsoft.Quota` RP registered (was missing). API confirms `cores` = 10,
  `StandardDsv6Family` = 10.
- `az quota update` → 16 for both: **`ContactSupport` / "Request failed."**
  (2 failed request IDs). Read path works; this subscription needs manual
  portal/support approval.
- Outcome recorded in `docs/evidence/phase7b/quota-7b0-gate.md` with exact
  portal steps. No VMs created, $0 cost, no region/SKU change.

### STEP 3 — Architecture update (docs only)

- Master roadmap: replace all 3 `ingress-nginx` refs (phase table 7B row,
  7B paragraph incl. `ingress-nginx` namespace, mesh paragraph
  "ingress-nginx stays north-south") with Gateway API + Envoy Gateway
  (north-south) / Istio Ambient future (east-west).
- Record: no AKS Application Routing (would embed its own Istio control plane;
  conflicts with separately-managed mesh add-on; managed add-on lacks Ambient).
- 7B subphase map 7B.0–7B.6 filed (user directive) for 7B.1+ execution.

### STEP 4 — Version preflight (researched 2026-09-21, verified)

- **Envoy Gateway v1.9.1** (NOT v1.8.4: v1.8 line supports K8s ≤1.35, EOL
  2026-11-08; v1.9 supports 1.33–1.36 incl. our 1.36.4, EOL 2027-02-14,
  bundles Gateway API v1.6.1). Pinned, never `latest`.
- **Argo CD v3.5.3** (latest stable 14 Sep 2026; tested K8s incl. 1.36;
  non-HA = documented eval/demo path; pin exact version for install).
- ingress-nginx retirement CONFIRMED (upstream halt Mar 2026, read-only repos,
  no security patches) — the no-install decision.

### STEP 5 — Cost plan

- Planned steady-state compute: 2×D4s_v6 ($0.554/h) + 1×D2s_v6 ($0.139/h) =
  **≈$0.693/h** → 2h session ≈$1.39 · 24h accidental ≈$16.63.
- Plus persistent public-Gateway networking (Standard LB frontend + public IP —
  small ongoing; no exact figure claimed without live verification) + existing
  stopped-state disks/IP/LB baseline.
- Quota increase itself costs $0 (limit change, no resources).

## 4. Verification

- Quota limits read live post-request (regional ≥16 AND Dsv6 ≥16) → 7B.0 PASS.
- Version facts sourced (release-notes/matrix/endoflife/pkg.go.dev/argo + k8s blogs).
- Evidence hygiene: no IDs/tokens in repo; raw CLI output redacted.

## 5. Acceptance criteria

- DECISION READY FOR 7B.1 only if: quota ≥16/≥16 verified live + arch docs
  updated + versions pinned + cost projection filed. Else BLOCKED with reason.
- "Things Not Yet Created" list complete (pool/gateway/Argo/P01/P02 absent,
  cluster Stopped).

## 6. Risks / rollback

- Manual-approval quota → STOP with exact portal steps (no auto-alternatives).
- This plan is docs + quota-limit change only; rollback = revert doc edits
  (quota increase is harmless limit metadata, optionally left as-is).
