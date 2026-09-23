# AKS-SRE-Platform — Current Tasks

> Updated: 2026-09-23 | Active Goal: **LOCAL PLATFORM L0–L3 + L1 PASS (Envoy Gateway v1.9.1 traffic-proven, arm64 app images loaded) — next gate is L4 (Argo CD), NOT started. Azure: Phase 7B.0 still BLOCKED on manual quota approval; teardown not executed (`docs/evidence/azure-teardown/`)**

## ACTIVE GOAL 2026-09-23 — LOCAL PLATFORM (L0–L3 + L1 DONE, local only)

STATUS: ✅ **L0–L2 PASS · L3 PASS · L1 PASS** — development runs on a **local**
Kubernetes runtime; no Azure resource was created, read for mutation, or destroyed.

- Tooling: `kind v0.33.0` + `helm v4.3.0` (brew, 2026-09-23); `kubectl v1.36.1`,
  `docker 29.6.1` (context `desktop-linux`); `argocd` CLI intentionally NOT installed.
- Host: arm64 (Apple Silicon), 16 GiB RAM. **Docker VM = 7.75 GiB** → the binding
  constraint; raising it is manual (macOS protects `settings-store.json`).
- Cluster `local-platform`: 1 control-plane + 2 workers, `kindest/node:v1.36.1`,
  kindnet CNI, StorageClass `standard`. Code:
  `local/kind/{cluster.yaml,create.sh,destroy.sh,load-image.sh,README.md}`.
- **L3 PASS** — Envoy Gateway **v1.9.1** (chart digest `sha256:91bae9ae…`) in
  `envoy-gateway-system`, `GatewayClass/portfolio-gatewayclass Accepted=True`,
  `Gateway/portfolio-gateway Accepted=True + Programmed=True`; `/proof` returned
  **200** with `LOCAL-ENVOY-GATEWAY-OK` and `/` returned **404** (control), with the
  Envoy access log + backend log proving the hop. MetalLB deliberately NOT installed
  (data plane is `ClusterIP` + `kubectl port-forward`). Code:
  `platform/envoy-gateway/`; evidence:
  `docs/evidence/local-platform/l3-envoy-gateway-PASS.md`.
- **L1 PASS** — `flashsale/order-api:local` + `flashsale/order-worker:local` built
  from source as **arm64** (103 289 453 / 101 153 927 bytes) and loaded to 3/3 nodes;
  `imagePullPolicy: Never` pods started natively (`RID: linux-arm64`) and failed only
  with the *expected* fail-closed config errors (`Auth:Jwt:SigningKey` /
  `MessagingConfigurationException`); **0** `exec format error`. No P01 source change.
- Image delivery: `kind load docker-image` **fails** here (containerd image store →
  nested index in the archive). `load-image.sh` now uses kind's documented
  workaround — single-platform export + `kind load image-archive` — verified on all
  nodes plus a `Never`-pull pod.
- Measured footprint after L3: **≈ 2.12 GiB of 7.75 GiB** (control-plane 1.377 GiB,
  workers 388/355 MiB) → ≈ 5.6 GiB headroom. Docker memory bump to 10 GiB is NOT
  needed for L4; schedule it **before L5**.
- HARD STOP: **L4 (Argo CD) is NOT started.** Do not install Argo CD, P01/P02, or
  observability without the next explicit go-ahead.


## ACTIVE GOAL 2026-09-21 — Phase 7B.0 (EXECUTED, DECISION: BLOCKED)

STATUS: 🛑 **BLOCKED on quota** — fresh quota live (stopped: 0/10+0/10; running math
8+2=10/10 zero headroom). `az quota update` →16 for `cores` + `StandardDsv6Family`:
both **FAILED (`ContactSupport`)** — subscription needs manual portal/support approval.
Exact portal steps: `docs/evidence/phase7b/quota-7b0-gate.md`. $0 spent, nothing created.

Architecture corrected (no platform installed): **NO ingress-nginx** (upstream retired
Mar 2026) → north-south = **Gateway API + Envoy Gateway v1.9.1** (v1.8 line lacks K8s 1.36;
EOL Feb 2027); future east-west = Istio Ambient (no AKS App Routing — embeds own Istio,
no Ambient support). **Argo CD v3.5.3** non-HA pinned. Cost plan: steady-state
2×D4s_v6+1×D2s_v6 ≈ **$0.693/h** (≈$1.39/2h, ≈$16.63/24h accidental) + persistent
public-IP/LB networking (unverified, not claimed exact).
Focus plan: `plans/2026-09-21-phase7b0-capacity-gate.md`.

Next: user completes portal quota increase → verify 16/16 live → authorize 7B.1.
7B.1 NOT started — STOP.

## ACTIVE GOAL 2026-09-21 — Phase 7A.2 (AUTHORIZED live run, strict gates)

STATUS: ✅ **7A FINAL PASS 2026-09-21** — temp `work` pool (1×D2s_v6) created + placement
proven + private `legacy-app:2d5d07…` pull (digest match, no secret, kubelet+AcrPull, NOT WI) +
WI federated `az acr show` (Reader-only temp UAMI, no secret) + full cleanup (ns → WI
resources → pool deleted, quota 8/10, cluster Stopped). Compute ≈$0.20 (16:16:59Z→16:35:45Z).
Evidence: `docs/evidence/phase7a/{user-pool-placement,private-acr-pull,workload-identity-runtime,phase7a-FINAL-PASS}.md`.
Code: `terraform/aks-foundation/wi-proof.tf` (+`enable_wi_proof`, default false).
Focus plan: `plans/2026-09-21-phase7a2-userpool-acrpull-wi-proof.md`. 7B NOT started — STOP.

## ACTIVE GOAL 2026-09-21 — Microservices/Saga/Kafka/Loki/Tempo/Mesh MANDATORY (plan filed, NOT started)

STATUS: 📋 PLAN FILED — user directive 2026-09-21 promotes microservices, Payment Service, Saga,
Kafka, Loki, Tempo, Service Mesh from "future optional" to **mandatory completion**
(phases 9–18). Focus plan: `plans/2026-09-21-microservices-mandatory-roadmap-9-to-18.md`.
Master roadmap `plans/2026-09-21-master-roadmap-7a-to-13.md` line 4 ("Out of scope…")
is SUPERSEDED by that plan — master file rewrite follows as a separate step.

HARD SEQUENCING GATE: no Phase 9+ implementation before baseline AKS + GitOps +
basic observability (7A→8) is green. Current execution focus is UNCHANGED:

- 7A.1 system-only apply (APPROVED, D4s_v6) — **DONE + STOPPED 2026-09-21**; next is 7A.2 (locked) per sections below.
- `.ai/harness/handoff/resume.md`: absent (checked 2026-09-21) — no pending handoff;
  `tasks/current.md` files remain the authority.

Next steps:
1. Rewrite master roadmap phases 9–18 (table + gates + DoD) from the focus plan.
2. Mirror Phase 9 decomposition targets into FlashSale-Backend `tasks/current.md` + roadmap.
3. Continue 7A.1 → 7B → … → 8 in order; open Phase 9 only after Phase 8 green.
4. Per-phase evidence dirs (`docs/evidence/kafka|...`) created at phase start, never retrofilled.

## ACTIVE GOAL 2026-09-21 — Phase 7A.1 APPLY (APPROVED system-only, D4s_v6)

## ACTIVE GOAL 2026-09-21 — Phase 7A.1 apply (master roadmap 7A→13 filed)

STATUS: ✅ **7A.1 PASS 2026-09-21** — AKS live verified (2×D4s_v6 Ready, kube-system healthy, OIDC+WI, AcrPull), then `Stopped`. Cost ≈ $0.19. Evidence: `docs/evidence/phase7a/system-foundation-PASS.md`. 7A.2+ locked.
Next: 7A.2 only after explicit approval — re-check BOTH quota tiers → enable temporary `D2s_v6` user pool → placement + private ACR-pull proof → delete pool same session → re-check quota → STOP cluster. Meanwhile the cluster stays Stopped (quota returned to `0/10`, no compute burn).
Note: post-apply `terraform plan` = **0/1/0** (no-op in-place drift from provider-block null/empty fields; no replace, no destroy) — Phase 8 debt, not actioned while stopped.

## SUPERSEDED — Phase 7A quota recovery (Dsv6 preflight DONE → led to the 7A.1 apply)

STATUS: ✅ **completed** — this preflight passed and produced the successful 7A.1 apply/stop above. Kept for history; do not read this section as a live gate.
Decision: Option 2 — SKU-only switch (D4as_v5 BLOCKED DASv5 0/0 → **Standard_D4s_v6**, Dsv6 quota 10, $0.277/h). No quota request, no RG destroy, no stale-plan reuse.

Round 2 preflight (fresh live eastasia, source commit `e9d086c`) — ALL GATES PASS:
- Regional vCPU `0/10` (remaining 10 ≥ 8) · `StandardDsv6Family` `0/10` (remaining 10 ≥ 8)
- `Standard_D4s_v6`: `Restrictions=[]`, 4 vCPU / 16 GiB, zones 1/2/3
- AKS `1.36` available · `aks-portfolio-dev` absent (`az aks list` = 0) · RG `rg-aks-platform-dev` exists, empty
- `terraform state list` = `data.azurerm_container_registry.shared` + `azurerm_resource_group.aks`; AKS + role assignment ABSENT
- `terraform plan -refresh-only` = **zero resource drift** (outputs only)
- `fmt -check -recursive` clean · `validate` Success · azurerm **5.6.0** locked, no `-upgrade`
- New saved plan `.local/phase7a-dsv6.tfplan` (gitignored): **2 to add, 0 to change, 0 to destroy** → creates `azurerm_kubernetes_cluster.aks` + `azurerm_role_assignment.aks_acr_pull`; RG unchanged; no Helm/app/monitoring/`work` pool resources
Evidence: `docs/evidence/phase7a/quota-recovery-dsv6-preflight.md`, `plan-summary.md`, `cost.md`.
Next: user approval → apply system-only → verify → STOP (user pool still 🔒).


## SUPERSEDED — Phase 7A SYSTEM-ONLY APPLY (APPROVED, strictly limited)

## ACTIVE GOAL 2026-09-21 — Phase 7A SYSTEM-ONLY APPLY

STATUS: 🟢 APPROVED — strictly limited to RG `rg-aks-platform-dev` + AKS `aks-portfolio-dev` + Terraform-managed AcrPull. User pool / proofs / Argo CD / ingress / P01-P02 🔒.

APPLY ATTEMPT 2026-09-21T07:59Z: **BLOCKED** — `ErrCode_InsufficientVCPUQuota` (standardDASv5Family 0/0 eastasia).
Partial state: RG created (empty, ~0 cost), AKS absent. No rerun, no destroy, no VM auto-switch per gate G.
Evidence: `docs/evidence/phase7a/apply-2026-09-21-BLOCKED.md`. Next: user picks quota-increase retry vs SKU-family switch vs RG cleanup.

Next steps: A freeze commit → B live safety → C init (no -upgrade) → D saved plan `.local/phase7a-system.tfplan` → E gate 3/0/0 → F apply exact plan → H–M verify/stop → FINAL REPORT → STOP (no user pool).

## ACTIVE GOAL 2026-09-21 — Phase 7A correction (superseded by apply approval above)

RESULT: PARTIAL — `current.md` updated with Phase 7A correction plan; APPLY BLOCKED pending REVIEW v2.

## ACTIVE GOAL 2026-09-21 — Phase 7A correction

STATUS: NOT YET APPROVED FOR APPLY — ⛔ STOP, no `terraform apply` until REVIEW v2 passes with explicit approval.

3 fixes required:
- FIX1 provider 5.x — bump/pin `azurerm` to 5.x line, `terraform init -upgrade`, re-validate `validate/fmt`.
- FIX2 evidence hygiene — no raw plan files in git; `gitignore` raw plans (`*.tfplan`, `plans/raw/`), only redacted evidence committed.
- FIX3 ACR RBAC terraform-managed + remote-state check — ACR role assignment managed by Terraform (not manual `az` CLI); verify remote-state backend (RG/storage/container/key `aks-foundation.tfstate`, encryption, locking) before replan.

Next steps (in order):
1. query ACR mode → 2. bump provider → 3. gitignore raw plans → 4. RBAC wiring → 5. replan → 6. REVIEW v2 → 7. STOP no apply.

## Lịch sử (giữ nguyên) — Active Goal cũ: Phase 7A AKS Foundation

**Trạng thái hiện tại:**
- [x] P01 PASS — Preflight / repo hygiene checks passed
- [x] P02 PASS — Terraform validate / fmt / structure checks passed
- [ ] NO cluster — Chưa có AKS cluster nào được tạo
- [ ] NO apply authorized — Chưa được phép chạy `terraform apply`

**Gate STOP trước apply:**
> ⛔ STOP — Không chạy `terraform apply` cho đến khi FINAL PRE-APPLY REVIEW (7A.5) hoàn tất và được approve explícit.

## Next Steps 7A.1 – 7A.5

- [x] **7A.1 Refactor done** — Tách module / layout terraform theo chuẩn Phase 7A (done)
- [ ] **7A.2 Providers** — Pin + cấu hình providers (azurerm, kubernetes, helm, null/time):
  - Kiểm tra versions.tf / providers.tf
  - Xác nhận backend config chưa apply
- [ ] **7A.3 Remote state** — Cấu hình remote state (Azure Storage backend):
  - Resource group / storage account / container
  - State key `aks-foundation.tfstate`, encryption, locking
  - `terraform init -migrate-state` dry-check (chưa migrate thật nếu chưa approve)
- [ ] **7A.4 System-only plan** — Chạy `terraform plan` scoped system-only:
  - Chỉ RG + VNet + AKS system nodepool, NO user workloads
  - Lưu plan file, review diff, không apply
- [ ] **7A.5 FINAL PRE-APPLY REVIEW** — Review cuối trước apply:
  - Checklist: P01/P02 evidence, plan output, cost/sku/region, network, auth/RBAC, secrets handling
  - Approve → mới được phép apply. Nếu chưa approve → giữ gate STOP.

## Notes

- `main.tf` cũ **superseded** — đã archive về `terraform/legacy/main.tf.disabled` (P0.1, 2026-09-21): không còn `.tf` runnable ở đó, secret đã xoá khỏi HEAD (P0.2). Active roots: `terraform/aks-foundation` + `terraform/data-protection` (con trỏ, root thật ở P01 `backup-storage`). Xem `terraform/README.md`.
- Helm `admin123` **đã xoá khỏi HEAD** (P0.2, 2026-09-21) — kể cả Secret plaintext trong `kubernetes/keda-trigger-auth.yaml`. Không commit password plaintext; dùng secret reference (Key Vault / External Secrets / Sealed Secrets). Credential cũ nếu từng dùng thật ở env nào → rotate.
- ⚠️ **KEDA scope (7A)**: `kubernetes/keda-trigger-auth.yaml` giờ chỉ reference secret do External Secrets tạo, nhưng điều đó **không** cho phép cài External Secrets Operator / KEDA / RabbitMQ trong Phase 7A. Manifest này **không** thuộc deployment 7A — ghi nhận như future workload/scaling concern; secret delivery mechanism sẽ quyết định ở scaling phase.
- ⚠️ **Cost safety**: cluster phải được stop sau khi lấy evidence: `az aks stop -g rg-aks-platform-dev -n aks-portfolio-dev`. Quota dự kiến 8/10 sau apply; proof window (user pool) sẽ chạm 10/10 trong vài phút.
- Mọi `apply` đều yêu cầu approval explícit sau 7A.5.
