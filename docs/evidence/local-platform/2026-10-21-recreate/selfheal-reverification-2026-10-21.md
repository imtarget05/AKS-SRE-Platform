# Self-heal re-measurement on the restored kind cluster (2026-10-21)

**Date:** 2026-10-21, 06:52–06:54 UTC (= **13:52–13:54 local, +07:00**)
**Branch:** `main` (tip `30ab2dd` before this slice) · **Cluster:**
`kind-local-platform` (kind, 3 nodes, `kindest/node:v1.36.1`, Argo CD **v3.5.5**)
**Application:** `flashsale`, project `portfolio`, revision
`fa081855609caf8889a4fdab12ab78ec6f390f17`
**Context:** **every** `kubectl` call in this run used `--context kind-local-platform`
(the ambient kubeconfig on this laptop points at the Azure cluster — §15.4 of the
re-verification document).
**Azure mutated:** **NO.** The only Azure calls were read-only (`az account show`,
`az aks list`, `az group list`, `kubectl --context aks-portfolio-dev get nodes`).
**Manifests changed to achieve this:** **NONE.** No repository file, no Application
manifest and no upstream commit was touched to produce either result.

---

## 0. Why this document exists

The platform was re-created on 2026-10-21 12:16–13:29 local
([`local-platform-recreate-evidence.md`](local-platform-recreate-evidence.md)) and
re-measured from scratch — but that run **did not re-inject drift**. The
self-heal claims of §9.5 of
[`../2026-10-20-reverify.md`](../2026-10-20-reverify.md) therefore stayed
**HISTORICAL**, because they had been measured on a kind cluster that no longer
existed.

**This document closes that gap**: the two self-heal classes were **re-injected
and re-measured on the restored cluster**, with a timestamp for every step.

| Claim | Before this run | After this run |
|---|---|---|
| spec-drift self-heal | HISTORICAL (2026-10-20, "~1 s") | **LOCAL_KIND_VERIFIED (re-measured 2026-10-21)** — 21 s drift → Synced |
| deleted-resource self-heal | HISTORICAL (2026-10-20, "~1 s") | **LOCAL_KIND_VERIFIED (re-measured 2026-10-21)** — 17 s delete → `readyReplicas=1` |
| extra `metadata.labels` drift | FINDING (§10, open) | **unchanged — NOT re-tested** (see §5) |

---

## 1. The configuration that was in force (not changed by this run)

Live, from the cluster (`selfheal-application-syncpolicy.txt`):

```yaml
syncPolicy:
  automated:
    prune: false
    selfHeal: true
  retry:
    limit: 5
    backoff: {duration: 10s, factor: 2, maxDuration: 3m}
  syncOptions:
    - PrunePropagationPolicy=foreground
    - RespectIgnoreDifferences=true
ignoreDifferences:
  - group: batch
    kind: Job
    jsonPointers:
      - /spec/selector
      - /spec/template/metadata/labels/controller-uid
      - /spec/template/metadata/labels/batch.kubernetes.io~1controller-uid
```

This is byte-for-byte the policy in
[`platform/argocd/applications/flashsale.yaml`](../../../platform/argocd/applications/flashsale.yaml).
Two things matter for the two cases below:

- **`selfHeal: true`** — Argo CD reconciles a hand-made change back to the
  manifest. This is what both cases exercise.
- **`prune: false`** — Argo CD does **not** delete cluster resources that are no
  longer in the manifest. It does **not** prevent Argo CD from *re-creating* a
  resource it owns that was deleted out-of-band — that is the self-heal path
  (case B), which is why case B passes even with `prune: false`.
- **`ignoreDifferences` covers only `batch/Job`** selector/pod-template labels.
  It does **not** touch `spec.replicas` of a Deployment, so case A is not
  suppressed by it.

---

## 2. CASE A — spec drift (scale) → self-heal

Full transcript with the raw poll log:
[`selfheal-case-a-spec-drift.txt`](selfheal-case-a-spec-drift.txt).

```console
$ kubectl --context kind-local-platform -n flashsale get deploy order-api -o jsonpath='replicas={.spec.replicas} ready={.status.readyReplicas}'
replicas=2 ready=2

$ kubectl --context kind-local-platform -n flashsale scale deploy/order-api --replicas=1
deployment.apps/order-api scaled
```

Timeline (UTC):

| # | Timestamp | Event |
|---|---|---|
| T0 | **06:52:26Z** | drift injected — `spec.replicas` 2 → 1 |
| — | 06:52:31Z | Argo CD: *"Requesting app refresh caused by object update"* (`order-api`) |
| — | 06:52:41Z | Argo CD: *"Updated sync status: Synced → OutOfSync"* (`reason=ResourceUpdated`) |
| — | 06:52:42Z | *"Initialized new operation … SelfHealAttemptsCount:1"* |
| — | 06:52:43Z | *"Applying resource Deployment/order-api in cluster …"* |
| T1 | **06:52:47Z** | *"Updated sync status: OutOfSync → Synced"* — `spec.replicas` = **2** |
| T2 | **06:53:10Z** | `readyReplicas` = 2, `availableReplicas` = 2 |

**Revert time = 21 s** (06:52:26Z → 06:52:47Z); fully converged (**ready**) at
**44 s**.

The reverted value is the manifest value, not a coincidence: the upstream local
overlay at revision `fa08185` pins

```yaml
replicas:
  - name: order-api
    count: 2
```

**VERDICT: PASS.**

---

## 3. CASE B — deleted resource → Argo CD re-creates it

Full transcript with the raw poll log:
[`selfheal-case-b-resource-deletion.txt`](selfheal-case-b-resource-deletion.txt).

```console
$ kubectl --context kind-local-platform -n flashsale get deploy payment-service -o jsonpath='replicas={.spec.replicas} ready={.status.readyReplicas}'
replicas=1 ready=1

$ kubectl --context kind-local-platform -n flashsale delete deploy/payment-service
deployment.apps "payment-service" deleted from flashsale namespace
```

Timeline (UTC):

| # | Timestamp | Event |
|---|---|---|
| T0 | **06:53:37Z** | Deployment deleted — the poll log shows `payment-service=GONE` |
| — | 06:53:38Z | *"Initiated automated sync"* + *"Updated sync status: Synced → OutOfSync"* |
| — | 06:53:38Z | *"Applying resource Deployment/payment-service in cluster …"* |
| — | 06:53:39Z | *"Adding resource result … message: 'deployment.apps/payment-service created'"* → *"OutOfSync → Synced"* |
| T1 | **06:53:54Z** | `readyReplicas` = **1** (pod scheduled and Ready) |

**Re-create time = 17 s** to `readyReplicas=1`; the object itself was back and
the Application `Synced` **2 s** after the delete.

**Proof it was Argo CD and not a leftover**: the re-created object carries
Argo CD's tracking annotation and Argo CD's own apply fingerprint —

```console
$ kubectl --context kind-local-platform -n flashsale get deploy payment-service \
    -o jsonpath='{.metadata.creationTimestamp}{"\n"}{.metadata.annotations.argocd\.argoproj\.io/tracking-id}{"\n"}'
2026-10-21T06:53:38Z
flashsale:apps/Deployment:flashsale/payment-service
```

**VERDICT: PASS.**

### 3.1 A side effect that is recorded, not hidden

The self-heal operation is a **partial** sync (`skipHooks:true` in the
controller log), so the PreSync hook `order-migrate` was **not** re-run by
either drift injection:

```console
$ kubectl --context kind-local-platform -n flashsale get job order-migrate \
    -o jsonpath='{.status.startTime} {.status.completionTime} {.status.succeeded}{"\n"}'
2026-10-21T06:34:16Z 2026-10-21T06:34:29Z 1
```

The job still carries the timestamps of the **last full sync** (06:34). This is
the expected behaviour of a partial self-heal sync and is worth stating, because
"self-heal re-ran the migration hook" would have been a false claim.

---

## 4. The re-measured numbers vs. the historical ones

| Class | 2026-10-20 run (HISTORICAL) | 2026-10-21 re-measurement (this document) |
|---|---|---|
| spec drift | "~1 s" (16:43:23 → 16:43:24) | **21 s** to Synced (06:52:26Z → 06:52:47Z); 44 s to `readyReplicas=2` |
| deleted resource | "~1 s" (16:44:04 → 16:44:05) | **17 s** to `readyReplicas=1` (06:53:37Z → 06:53:54Z); 2 s to the object being back |

**The re-measured numbers are the ones claimed from now on.** The 2026-10-20
figures were recorded on the **destroyed** cluster and were almost certainly
measured against a *polled* Argo CD status rather than against the controller's
own event timestamps; they are kept in the record as history, not as the current
measurement. Nothing about the platform's behaviour changed between the two runs
— the same `selfHeal: true` policy, the same Argo CD v3.5.5, the same upstream
revision family. The difference is **what the clock was measuring**.

---

## 5. What was deliberately **not** re-tested

- **Extra `metadata.labels` drift** — the **FINDING** of §10 of the
  re-verification document (Argo CD v3.5.5 does not diff an *added*
  `metadata.labels` entry, so a hand-added label is not reverted and the
  Application stays `Synced`). **Not re-injected here** and **not re-measured**;
  the finding stands unchanged and **open**.
- **Label-drift is not re-run by instruction** — the task explicitly asked not
  to repeat it, because it is a recorded finding, not a claim to re-assert.

---

## 6. Files in this evidence set

| File | Content |
|---|---|
| `selfheal-reverification-2026-10-21.md` | this document — the narrative, the config in force, both verdicts |
| `selfheal-case-a-spec-drift.txt` | case A: command, before/after, 1 s poll log, controller-log excerpt, verdict |
| `selfheal-case-b-resource-deletion.txt` | case B: command, before/after, 1 s poll log, controller-log excerpt, verdict |
| `selfheal-argocd-controller.log.txt` | the raw `argocd-application-controller` log lines for 06:52–06:54Z |
| `selfheal-application-syncpolicy.txt` | the live Application YAML (syncPolicy / ignoreDifferences / revision) |

---

## 7. Status of every claim after this run

| Claim | Kind | State |
|---|---|---|
| kind cluster 3/3 Ready, v1.36.1 | **LOCAL_KIND_VERIFIED** | re-measured 2026-10-21 |
| Argo CD 7/7 Running, pinned v3.5.5 | **LOCAL_KIND_VERIFIED** | re-measured 2026-10-21 |
| `flashsale` Application `Synced` + `Healthy` | **LOCAL_KIND_VERIFIED** | re-measured 2026-10-21, revision `fa08185…` |
| `order-migrate` PreSync hook `Complete 1/1`, exit 0 | **LOCAL_KIND_VERIFIED** | re-measured 2026-10-21 |
| AppProject allowlist refuses a bad destination | **LOCAL_KIND_VERIFIED** | re-measured 2026-10-21, 1/1 negative control |
| **spec-drift self-heal** | **LOCAL_KIND_VERIFIED (re-measured 2026-10-21)** | **this document, §2** — 21 s drift → Synced |
| **deleted-resource self-heal** | **LOCAL_KIND_VERIFIED (re-measured 2026-10-21)** | **this document, §3** — 17 s delete → `readyReplicas=1` |
| extra `metadata.labels` are NOT self-healed | **FINDING, open** | unchanged, not re-tested (§5) |
| `legacyapp` deployed | **NOT VERIFIED** | not approved (ADR-015) |
| business E2E / concurrency flow | **NOT VERIFIED** | not re-run |
| `sre-demo-api` pod-level RED metrics | **NOT VERIFIED** | destroyed ACR registry |
| Azure cluster running / billable | **AZURE_CLOUD_LIVE_CONFIRMED** | re-confirmed read-only 2026-10-21 ~14:0x; teardown **prepared, NOT executed** |
| `terraform apply` of the AKS foundation | **AZURE_CLOUD_APPLY_NOT_VERIFIED** | still no committed apply output |

**Owner for the open items: P03** — (1) the billable Azure cluster
(`docs/runbooks/azure-teardown-runbook.md`, prepared, not executed), (2) the
label-drift finding, (3) the orphaned `azurerm` remote state.

---

## 8. Addendum — the host degraded the cluster AGAIN, ~25 minutes after the measurement

**This addendum is recorded because it happened after the measurement above
and changes the "the cluster is green" statement.** It does **not** change the
self-heal verdict.

### 8.1 Timeline

| Timestamp (UTC) | Observation |
|---|---|
| 06:54 | the self-heal measurement is complete; the cluster is healthy — `order-api` `readyReplicas=2` (since 06:53:10Z), `payment-service` `readyReplicas=1` (since 06:53:54Z), all other pods `Running` with **0 restarts** |
| ~07:19 | the **host** saturates: `uptime` load average **50–78**, `vm.swapusage` **11.1–11.6 GB of 12 GB used** |
| 07:2x | the data tier starts failing its own probes: `postgres-0` `pg_isready … timed out after 1s`, `redis` `redis-cli ping … timed out after 1s`, `kafka-0` `dial tcp …:9092: i/o timeout`, `rabbitmq-0` `rabbitmq-diagnostics -q ping … timed out after 10s` |
| 07:2x | `rabbitmq-0` hits the Erlang **`system_memory_high_watermark`** alarm and crash-loops (17 restarts by 08:04) |
| 07:3x | `order-api` cannot start: `AddOrderQueue` → `FlashSale.Infrastructure.Messaging.MessagingServiceCollectionExtensions.AddOrderQueue` throws at DI build time because RabbitMQ is down → both `order-api` pods `CrashLoopBackOff` (22 and 26 restarts) |
| ~07:56 | `kube-apiserver` is **re-created inside the kind control-plane container** (`crictl ps` → `CREATED 8 minutes ago`), and the API server stops answering: `Unable to connect to the server: net/http: TLS handshake timeout` |
| 08:02 | partial recovery: `rabbitmq-0` and one `order-api` pod reach `1/1`, then `rabbitmq-0` flaps back to `0/1` |
| 08:04 (capture) | `flashsale` = **`Synced` / `Progressing`** — GitOps is fine, the *workload* is not |
| **08:06:22Z** | **full self-recovery**: `flashsale` → **`Synced` / `Healthy`**, every pod `1/1 Running` (`order-api` ×2, `rabbitmq-0`, `postgres-0`, `redis-0`, `kafka-0`, `order-worker`, `payment-service`), host load back to **24** |

Raw capture: [`host-degradation-2026-10-21.txt`](host-degradation-2026-10-21.txt).

### 8.2 Why this is NOT a self-heal regression

- The measurement window (**06:52:26Z → 06:53:54Z**) is **35+ minutes before**
  the first failure signal, and every artefact in §2 and §3 shows a healthy
  cluster (0 restarts, `readyReplicas` reached, Argo CD `Synced`).
- **The failure chain runs downwards through the data tier**, not through the
  GitOps layer: memory pressure → `postgres`/`redis`/`kafka`/`rabbitmq` probe
  timeouts → `order-api` cannot build its RabbitMQ queue service → crash loop.
  Argo CD's own logs show no drift and no sync error; the Application never
  left `Synced`.
- **Nothing in the repository changed** between the green state and the
  degraded state. The failure is a property of the **host**, which is shared
  with other repositories' containers (`ob-*`, `kho-tra-sua-*`, `quanlykho-*`,
  …) and is under **swap pressure**.

This is the **same class** of event already documented in §2.1, §9.7, §11 #6,
§13 and §16.4 — the third+ instance, and the reason §13.5's recommendation
(isolate the kind cluster in its own Docker context / VM) is now a
prerequisite for any durable runtime claim, not a nice-to-have.

### 8.3 One accidental but useful confirmation

`payment-service` — **the object Argo CD re-created at 06:53:38Z** — was still
`1/1 Running` at 08:04 (10 restarts, all caused by the host event). The
self-healed object therefore **survived the host degradation** and was never
deleted again. That is not a separate claim; it is simply what the evidence
shows.

### 8.4 Status correction

| Statement | State after this addendum |
|---|---|
| self-heal of spec drift / deleted resource | **unchanged — LOCAL_KIND_VERIFIED (re-measured 2026-10-21, 06:52–06:54Z)** |
| the cluster is green **right now** | **YES again — it recovered on its own at 08:06:22Z** (`Synced` / `Healthy`, every pod `1/1 Running`). It was **degraded** from ~07:19Z to ~08:06Z by the host. **No cluster mutation was performed by this slice** — the recovery was the platform's own, exactly as §16.4 describes. |
| `AZURE_CLOUD_APPLY_NOT_VERIFIED` | unchanged |
| label-drift finding | unchanged, still open |

**The generalisable rule, now measured three times (§2.1, §9.7, §16.4 and
now §8):** *a runtime claim measured on this kind cluster is valid for the
minutes it was measured in, and no longer. The platform is fine; the
measurement surface is not.* That is an argument for isolating the cluster in
its own Docker context / VM (§13.5) — and for **publishing timestamps with
every runtime claim**, which is what §2, §3 and §8 of this document do.
