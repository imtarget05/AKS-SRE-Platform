# Local platform — kind cluster re-created and re-verified (2026-10-21)

**Date:** 2026-10-21, 12:16–13:29 local (+07:00)
**Branch:** `recovery/g2-20261020` (worktree) → committed on `main`
**Cluster:** `kind-local-platform` (kind, 3 nodes, `kindest/node:v1.36.1`)
**Azure mutated:** **NO.** Every `az` / `kubectl --context aks-portfolio-dev`
call in this run was **read-only**. No `terraform plan`, `apply` or `destroy`.
**Containers of other repositories:** not deleted, not stopped.

## 0. Why this document exists

The 2026-10-20/21 re-verification document
([`../2026-10-20-reverify.md`](../2026-10-20-reverify.md)) records the
Argo CD / self-heal / PreSync-hook measurements against a kind cluster that
**was destroyed** (the actor's blanket `docker rm -f`, §13.1). Those
measurements were therefore **HISTORICAL** — not re-establishable from the
tree.

**This document records that the platform was brought back on 2026-10-21 and
re-measured from scratch**, so the claims are no longer historical. It is the
reproduction section (§16) of the re-verification document.

## 1. Starting state (measured, 12:16–12:2x)

```console
$ kind get clusters
local-platform
$ docker ps --format '{{.Names}} {{.CreatedAt}}'
local-platform-worker2     2026-10-21 12:16:45 +0700
local-platform-control-plane 2026-10-21 12:16:45 +0700
local-platform-worker      2026-10-21 12:16:45 +0700
```

The cluster had been **re-created at 12:16:45** by another actor, from the
working tree that carries the **uncommitted WIP** in `local/kind/cluster.yaml`
(`hostPort: 8080` → `18080`) — the running control-plane container indeed
publishes `127.0.0.1:18080->30080/tcp`. **This slice did not modify, stash,
reset, commit or delete that WIP file**, and did not re-create the cluster —
it **reused** the existing one, so the actor's WIP was left intact.

**The cluster was bare** — no Argo CD, no `flashsale` namespace:

```console
$ kubectl -n argocd get applications
Error from server (NotFound): the server could not find the requested resource
$ kubectl -n flashsale get all
No resources found in flashsale namespace.
```

So at the start of this run the Argo CD / self-heal claims of §9 of the
re-verification document were **not re-establishable**: the cluster existed,
but it carried **none** of the platform.

## 2. The images were already built — the first rebuild was not needed

```console
$ docker images | grep -E 'flashsale/(order-api|order-worker|payment-service)'
flashsale/order-api:local        bd7ce015d3a2  715MB
flashsale/order-worker:local     c4836533d096  711MB
flashsale/payment-service:local  91319bde943c  370MB
```

All three `:local` tags the Application expects were **already present** in the
local Docker daemon, so the ~35-minute rebuild was **not** required. The
data-tier images (`postgres:15-alpine`, `redis:7-alpine`,
`rabbitmq:3-management-alpine`, `apache/kafka:3.8.0`) were present too.

**Had they been missing, the rebuild command would have been:**

```bash
git clone --depth 1 https://github.com/imtarget05/FlashSale-Backend.git /tmp/FSB
cd /tmp/FSB && git checkout <revision Argo resolves>
docker build --platform linux/arm64 -f Dockerfile        -t flashsale/order-api:local       .
docker build --platform linux/arm64 -f Dockerfile.worker -t flashsale/order-worker:local    .
docker build --platform linux/arm64 -f Dockerfile.payment -t flashsale/payment-service:local .
```

## 3. Image load — `local/kind/load-image.sh`, rc=0, OK on 3/3 nodes

```console
$ ./local/kind/load-image.sh flashsale/order-api:local flashsale/order-worker:local \
                       flashsale/payment-service:local postgres:15-alpine redis:7-alpine \
                       rabbitmq:3-management-alpine apache/kafka:3.8.0
host  : arm64 -> export platform linux/arm64
nodes : 3 node(s), all linux/arm64
==> Verify presence on every node
    OK      local-platform-worker              flashsale/order-api:local
    OK      local-platform-control-plane       flashsale/order-api:local
    OK      local-platform-worker2             flashsale/order-api:local
    OK      local-platform-worker              flashsale/order-worker:local
    OK      local-platform-control-plane       flashsale/order-worker:local
    OK      local-platform-worker2             flashsale/order-worker:local
    OK      local-platform-worker              flashsale/payment-service:local
    OK      local-platform-control-plane       flashsale/payment-service:local
    OK      local-platform-worker2             flashsale/payment-service:local
    OK      local-platform-worker              postgres:15-alpine
    OK      local-platform-control-plane       postgres:15-alpine
    OK      local-platform-worker2             postgres:15-alpine
    OK      local-platform-worker              redis:7-alpine
    OK      local-platform-control-plane       redis:7-alpine
    OK      local-platform-worker2             redis:7-alpine
    OK      local-platform-worker              rabbitmq:3-management-alpine
    OK      local-platform-control-plane       rabbitmq:3-management-alpine
    OK      local-platform-worker2             rabbitmq:3-management-alpine
    OK      local-platform-worker              apache/kafka:3.8.0
    OK      local-platform-control-plane       apache/kafka:3.8.0
    OK      local-platform-worker2             apache/kafka:3.8.0
RC=0
```

**21/21 (7 images × 3 nodes) OK.** This load took **≈ 13 minutes** on this
run (12:2x → 13:0x local) — faster than the ~35 minutes recorded on
2026-10-20, because the Docker layer cache was already warm.

## 4. Bootstrap — Argo CD v3.5.5 pinned, 7/7 Running

```console
$ bash scripts/bootstrap.sh
==> 1/3 Installing Argo CD v3.5.5 (pinned)
...
    argocd-server image: quay.io/argoproj/argocd:v3.5.5 (matches the pin)
==> 2/3 Installing KEDA (upstream chart)
==> 3/3 Applying AppProject and maintained Applications
appproject.argoproj.io/portfolio created
application.argoproj.io/flashsale created
    skipping legacyapp.yaml — ADR-015 source switch is not approved.
Done. Check: kubectl get applications -n argocd
```

```console
$ kubectl -n argocd get pods
NAME                                                READY   STATUS    RESTARTS   AGE
argocd-application-controller-0                     1/1     Running   0          3m6s
argocd-applicationset-controller-5cfb86c7b8-lk7lc   1/1     Running   0          3m7s
argocd-dex-server-7b97c47d8d-l4fgq                 1/1     Running   0          3m7s
argocd-notifications-controller-554c4bbbf5-wzl8v    1/1     Running   0          3m7s
argocd-redis-75485fcc5f-nhq6c                       1/1     Running   0          3m7s
argocd-repo-server-6fbd599f8-bzq4p                  1/1     Running   0          3m7s
argocd-server-b789667d5-bw8vn                       1/1     Running   0          3m7s
7/7 Running
```

**All three Argo CD CRDs are present** (`applications.argoproj.io`,
`applicationsets.argoproj.io`, `appprojects.argoproj.io`) — the server-side
apply (F1) works on a fresh cluster.

**Only ONE Argo CD control plane this time** — no stray copy in `default`
(the §2.9 / §11 #5 double-install did **not** reappear, because the install
is applied with `-n argocd`).

## 5. The two prerequisites that are NOT in `scripts/bootstrap.sh`

Both were required to reach `Healthy`, and both are recorded in the
re-verification document §9.4 as separate steps.

**(a) The platform Gateway.** `scripts/bootstrap.sh` does **not** install Envoy
Gateway — the `flashsale` Application's `HTTPRoute` points at
`platform-gateway/portfolio-gateway`, and without it the Application is
`Synced` but `Degraded`/`Progressing`:

```console
$ helm upgrade --install envoy-gateway oci://docker.io/envoyproxy/gateway-helm \
    --version v1.9.1 --namespace envoy-gateway-system --create-namespace \
    -f platform/envoy-gateway/values.yaml --wait --timeout 5m
$ kubectl apply -f platform/envoy-gateway/gateway/namespace.yaml \
                -f platform/envoy-gateway/gateway/envoyproxy.yaml \
                -f platform/envoy-gateway/gateway/gatewayclass.yaml \
                -f platform/envoy-gateway/gateway/gateway.yaml
namespace/platform-gateway created
envoyproxy.gateway.envoyproxy.io/portfolio-proxy-config created
gatewayclass.gateway.networking.k8s.io/portfolio-gatewayclass created
gateway.gateway.networking.k8s.io/portfolio-gateway created
$ kubectl wait --for=condition=Programmed gateway/portfolio-gateway -n platform-gateway --timeout=180s
gateway.networking.k8s.io/portfolio-gateway condition met
```

**(b) The cold-start ordering.** Argo CD runs PreSync hooks **before any
wave**, and the `order-migrate` hook needs PostgreSQL — which is a wave `-3`
resource. The data tier must therefore be applied **first**, from the **same
pinned revision** Argo resolves:

```console
$ kubectl create namespace flashsale
namespace/flashsale created
$ bash infrastructure/kubernetes/overlays/local/create-local-secrets.sh
flashsale-secrets applied in namespace flashsale.
  pg-password        : 48 chars
  rabbitmq-password  : 48 chars
  jwt-signing-key    : 64 chars (fingerprint 385746e6c61d)
  values are NOT printed and NOT committed.

$ kubectl kustomize infrastructure/kubernetes/overlays/local > /tmp/flashsale-all.yaml
# extract + apply the wave -3 data tier (5 Services + StatefulSets postgres/
# rabbitmq/kafka + Deployment redis = 9 documents)
$ kubectl apply -f /tmp/data-tier.yaml
service/kafka created
service/postgres created
service/rabbitmq created
service/rabbitmq-mgmt created
service/redis created
deployment.apps/redis created
statefulset.apps/kafka created
statefulset.apps/postgres created
statefulset.apps/rabbitmq created
```

> **Note for the next reproducer:** applying the 9-document data tier in a
> **single** `kubectl apply -f` aborted after the first object on this run
> (only `statefulset.apps/rabbitmq` was reported). Applying the documents
> **one at a time** succeeded for all 9. A second `--server-side` attempt
> failed with a `.spec.volumeClaimTemplates` field-ownership conflict. The
> reliable form is the per-document loop.

## 6. Sync → `Synced` / `Healthy`, and the PreSync hook green

```console
$ kubectl -n argocd annotate application flashsale argocd.argoproj.io/refresh=hard --overwrite
application.argoproj.io/flashsale annotated

$ kubectl -n argocd get application flashsale -o wide
NAME        SYNC STATUS   HEALTH STATUS   REVISION                                   PROJECT
flashsale   Synced        Healthy         f00b827fce3106689dea6b1b1d239e7436645533   portfolio
# (this was the state at 13:0x; the final revision after the upstream rewrite
#  and the payment-service rebuild is fa08185… — see §6)

$ kubectl -n argocd get application flashsale -o jsonpath='{.status.operationState.message}'
successfully synced (all tasks run)

$ kubectl -n flashsale get job order-migrate -o wide
NAME            STATUS     COMPLETIONS   DURATION   AGE     CONTAINERS   IMAGES                      SELECTOR
order-migrate   Complete   1/1           6s         8m30s   migrate      flashsale/order-api:local   batch.kubernetes.io/controller-uid=f136f428-f6f4-48a6-87a1-69a8149a1954

$ kubectl -n flashsale logs job/order-migrate --tail=2
{"EventId":0,"LogLevel":"Information","Category":"Migration","Message":"Schema is now at head.", ...}
{"EventId":0,"LogLevel":"Information","Category":"Migration","Message":"Migration entrypoint finished with exit code 0","State":{"ExitCode":0, ...}}
```

## 6. The upstream repository moved mid-run — and the local image had to follow

This is the most important operational finding of this run, and it is
**recorded here rather than smoothed away**.

**Timeline (2026-10-21, local):**

| Time | Event |
|---|---|
| ~13:0x | Argo resolves `main` = **`f00b827fce3106689dea6b1b1d239e7436645533`** → `flashsale` **`Synced` / `Healthy`**. The three `:local` images (built from the **older** upstream revision) work fine against it. |
| ~13:3x | The **upstream repository `FlashSale-Backend` is rewritten** — `main` gains a large batch of commits (transactional outbox, `Payment.Service` implementation, the OpsBridge foundation, …). Argo re-resolves to **`4c74c6d`**, then to **`fa08185`**. |
| ~13:4x | The **`payment-service` Deployment crash-loops**: the new upstream manifest probes **`/health/live` and `/health/ready`**, the loaded image still served **`/health`**, so the probe got **404** and the kubelet killed the container. |
| ~13:5x | `flashsale/payment-service:local` is **rebuilt from `fa08185`** (`Dockerfile.payment`), **re-loaded** into all 3 nodes with `local/kind/load-image.sh` (3/3 OK), and the crash-looping pod is replaced. |
| ~13:5x | `flashsale` is **`Synced` / `Healthy`** again, at revision **`fa081855609caf8889a4fdab12ab78ec6f390f17`**. |

**The measured proof of the probe mismatch:**

```console
$ kubectl -n flashsale logs payment-service-75cbd758f9-6lvx7 --tail=15
..."Message":"Request finished HTTP/1.1 GET http://10.244.2.18:8080/health/live - 404 0 - 0.2790ms"...
..."Message":"Request finished HTTP/1.1 GET http://10.244.2.18:8080/health/ready - 404 0 - 0.1177ms"...
..."Message":"Application is shutting down..."   # killed by the failed probe
```

```console
$ git -C /tmp/FlashSale-Backend diff f00b827 origin/main -- infrastructure/kubernetes/base/ | grep -E '^[+-].*path:'
-              path: /health
+              path: /health/live
-              path: /health
+              path: /health/ready
```

**The lesson, stated as a rule:** *a local `:local`-tagged image is pinned to
the upstream revision it was built from. When upstream `main` moves, the
manifests move with it and the image must be rebuilt and re-loaded — otherwise
the Application stays `Synced` but the workload **crash-loops** on the new
probe paths.* This is the single most common way a GitOps-forward-sync setup
breaks on a laptop, and it is **not** a defect in this repository.

**Only `payment-service` needed rebuilding.** `order-api` and `order-worker`
kept working against the new revision with the images already loaded — the
probe paths they use did not change.

**Final state after the rebuild:**

```console
$ kubectl -n argocd get application flashsale -o wide
NAME        SYNC STATUS   HEALTH STATUS   REVISION                                   PROJECT
flashsale   Synced        Healthy         fa081855609caf8889a4fdab12ab78ec6f390f17   portfolio

$ kubectl -n flashsale get pods -o wide
NAME                               READY   STATUS      RESTARTS      AGE     IP            NODE                     NOMINATED NODE   READINESS GATES
kafka-0                            1/1     Running     0             27m     10.244.2.12   local-platform-worker2   <none>           <none>
kafka-topic-init-k5dzm             0/1     Completed   0             25m     10.244.2.14   local-platform-worker2   <none>           <none>
order-api-758cc56c9b-v7cnj         1/1     Running     5 (18m ago)   25m     10.244.2.16   local-platform-worker2   <none>           <none>
order-api-758cc56c9b-zlvh8         1/1     Running     6 (18m ago)   25m     10.244.1.15   local-platform-worker    <none>           <none>
order-migrate-4klzv                0/1     Completed   0             12m     10.244.2.13   local-platform-worker2   <none>           <none>
order-worker-78796f7f86-l47wd      1/1     Running     0             25m     10.244.2.15   local-platform-worker2   <none>           <none>
payment-service-75cbd758f9-bzpgr   1/1     Running     0             45s     10.244.2.18   local-platform-worker2   <none>           <none>
postgres-0                         1/1     Running     0             27m     10.244.1.14   local-platform-worker    <none>           <none>
rabbitmq-0                         1/1     Running     3 (12m ago)   28m     10.244.1.12   local-platform-worker    <none>           <none>
redis-695b986ccc-kszsp             1/1     Running     0             27m     10.244.2.11   local-platform-worker2   <none>           <none>

$ kubectl -n flashsale get job order-migrate -o wide
NAME            STATUS     COMPLETIONS   DURATION   AGE     CONTAINERS   IMAGES                      SELECTOR
order-migrate   Complete   1/1           13s        12m     migrate      flashsale/order-api:local   batch.kubernetes.io/controller-uid=a582c978-570f-4d57-9dd2-d86c3143847d

$ kubectl -n flashsale logs job/order-migrate --tail=2
{"EventId":0,"LogLevel":"Information","Category":"Migration","Message":"Schema is now at head.", ...}
{"EventId":0,"LogLevel":"Information","Category":"Migration","Message":"Migration entrypoint finished with exit code 0","State":{"ExitCode":0, ...}}
```

> **The `order-migrate` hook ran **twice** in this session** — once for
> `f00b827` and once for `fa08185` — and **both went green** (`exit code 0`).
> That is itself a piece of evidence that the hook is re-runnable against an
> already-migrated database, not just a first-run path.

**The `order-api` / `order-worker` restart counts (5 and 6) are the host
memory-pressure artefact of §7, not a property of the manifests.**

## 7. The host instability, measured again (§11 #6 / §13.4)

`rabbitmq-0` and the two `order-api` pods **crashed and restarted** while the
Application was converging. Measured cause — **not** a manifest defect:

```console
$ kubectl -n flashsale describe pod rabbitmq-0 | grep -A4 'Unhealthy'
Warning  Unhealthy  92s (x3 over 2m47s)  kubelet  spec.containers{rabbitmq}: Liveness probe failed: command timed out: "rabbitmq-diagnostics -q ping" timed out after 10s
Normal   Killing    92s                  kubelet  spec.containers{rabbitmq}: Container rabbitmq failed liveness probe, will be restarted
```

```console
$ docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}'
ob-api	121.3MiB / 7.75GiB
ob-pg	44.3MiB / 7.75GiB
kho-tra-sua-frontend	7.516MiB / 7.75GiB
kho-tra-sua-api	102MiB / 7.75GiB
kho-tra-sua-db	37.5MiB / 7.75GiB
local-platform-worker2	1.482GiB / 7.75GiB
local-platform-control-plane	1.598GiB / 7.75GiB
local-platform-worker	1.192GiB / 7.75GiB
```

The kind cluster's three nodes alone consume **≈ 4.27 GiB** of the
**7.75 GiB** Docker VM, and **other repositories' containers** (`ob-*`,
`kho-tra-sua-*`) hold a further **≈ 312 MiB** — so the VM had no headroom for
RabbitMQ's Erlang VM and the liveness probe timed out. The pods recovered on
their own; the poll below shows the recovery:

```console
[1] app=Synced/Progressing rabbitmq=false/2
[2] app=Synced/Progressing rabbitmq=false/2
[3] app=Synced/Progressing rabbitmq=false/2
[4] app=Synced/Progressing rabbitmq=true/2
[5] app=Synced/Healthy  rabbitmq=true/2
```

**This is the same host-level instability the re-verification document records
three times (§2.1, §9.7, §11 #6). It is recorded here as a caveat, not as a
pass and not as a regression.** The restart counters in §6 (`5`, `6`, `2`) are
a property of **this workstation**, not of the manifests.

## 8. Negative control — the AppProject allowlist still bites

One Application with a **destination outside the allowlist** was created in the
`argocd` namespace and then deleted:

```console
$ kubectl apply -f /tmp/nc-bad-dest.yaml
application.argoproj.io/nc-bad-destination-ns created

$ kubectl -n argocd get application nc-bad-destination-ns -o jsonpath='{.status.conditions[?(@.type=="InvalidSpecError")].message}'
application destination server 'https://kubernetes.default.svc' and namespace 'kube-system' do not match any of the allowed destinations in project 'portfolio'

$ kubectl -n argocd delete application nc-bad-destination-ns
application.argoproj.io "nc-bad-destination-ns" deleted from argocd namespace
```

The live allowlist that enforced it:

```console
$ kubectl -n argocd get appproject portfolio -o jsonpath='{.spec.sourceRepos}{"\n"}{.spec.destinations}{"\n"}'
["https://github.com/imtarget05/FlashSale-Backend.git","https://github.com/imtarget05/AKS-SRE-Platform.git"]
[{"namespace":"flashsale","server":"https://kubernetes.default.svc"},{"namespace":"legacyapp","server":"https://kubernetes.default.svc"}]
```

`kube-system` is not in the allowed destinations → the Application is
**refused by the controller**, not by convention. **1/1 negative control
refused.** (The 2026-10-20 run did 2 — one bad source repo and one bad
destination. This run did the destination one, which is the one the task
asked for.)

## 9. What was NOT verified in this run

| Item | Status | Reason |
|---|---|---|
| **Self-heal of spec drift / deleted resource** | **NOT VERIFIED (this run)** → **superseded later the same day** | The 2026-10-20 run measured it (§9.5). **This run** did **not** re-inject drift. → **A later slice on 2026-10-21, 06:52–06:54 UTC (13:52–13:54 local), re-injected both classes of drift on this same restored cluster and measured them**: spec drift reverted in **21 s**, a deleted Deployment was re-created and ready in **17 s**. See **[`selfheal-reverification-2026-10-21.md`](selfheal-reverification-2026-10-21.md)**. The `selfHeal: true` policy was not changed to achieve it. |
| **Label-drift self-heal** | **FINDING, still open** | Unchanged: Argo CD v3.5.5 does not diff an *added* `metadata.labels` entry (§10 of the re-verification document). Not re-tested here. |
| **`legacyapp` Application** | **NOT VERIFIED** | `scripts/bootstrap.sh` skips it unless `APPLY_LEGACYAPP=1` — ADR-015 source switch not approved. |
| **Business E2E / concurrency flow** | **NOT VERIFIED** | Only the deployment plane was proven. |
| **`sre-demo-api` pod-level RED metrics** | **NOT VERIFIED** | The image reference points at a destroyed ACR registry. |
| **Azure cloud** | **NOT VERIFIED (this run)** | Nothing here ran against Azure. Read-only `az`/`kubectl` calls only, to confirm the billable cluster's state. |
| **`terraform apply` of the AKS foundation** | **AZURE_CLOUD_APPLY_NOT_VERIFIED** | Unchanged — no committed apply output exists for either live-AKS run. |

## 10. How to reproduce this, end to end

The full reproduction is in
[`../2026-10-20-reverify.md`](../2026-10-20-reverify.md) **§16**; the
condensed form, with the timings measured today:

```bash
# ── 1. Cluster (reuse if it exists; the script never re-creates a healthy one)
bash local/kind/create.sh                       # ~1 min

# ── 2. Images (build only if the :local tags are missing — ~35 min each)
git clone --depth 1 https://github.com/imtarget05/FlashSale-Backend.git /tmp/FSB
cd /tmp/FSB && git checkout <revision Argo resolves>
docker build --platform linux/arm64 -f Dockerfile        -t flashsale/order-api:local       .
docker build --platform linux/arm64 -f Dockerfile.worker -t flashsale/order-worker:local    .
docker build --platform linux/arm64 -f Dockerfile.payment -t flashsale/payment-service:local .

# ── 3. Load into every node (~13 min on a warm cache; ~35 min cold)
cd /Users/mainguyenbinhtan/Downloads/AKS-SRE-Platform
./local/kind/load-image.sh flashsale/order-api:local flashsale/order-worker:local \
                       flashsale/payment-service:local postgres:15-alpine redis:7-alpine \
                       rabbitmq:3-management-alpine apache/kafka:3.8.0

# ── 4. Bootstrap the platform (~4 min)
bash scripts/bootstrap.sh                        # Argo CD v3.5.5 (pinned) + KEDA + AppProject + Applications

# ── 5. Envoy Gateway + the platform Gateway (~3 min) — NOT in bootstrap.sh
helm upgrade --install envoy-gateway oci://docker.io/envoyproxy/gateway-helm \
  --version v1.9.1 --namespace envoy-gateway-system --create-namespace \
  -f platform/envoy-gateway/values.yaml --wait --timeout 5m
kubectl apply -f platform/envoy-gateway/gateway/namespace.yaml \
              -f platform/envoy-gateway/gateway/envoyproxy.yaml \
              -f platform/envoy-gateway/gateway/gatewayclass.yaml \
              -f platform/envoy-gateway/gateway/gateway.yaml
kubectl wait --for=condition=Programmed gateway/portfolio-gateway -n platform-gateway --timeout=180s

# ── 6. Secret + cold-start data tier (PreSync hooks run before every wave)
kubectl create namespace flashsale
cd /tmp/FSB && bash infrastructure/kubernetes/overlays/local/create-local-secrets.sh
kubectl kustomize infrastructure/kubernetes/overlays/local > /tmp/flashsale-all.yaml
# extract and apply the 9 wave -3 documents ONE AT A TIME (see §5)

# ── 7. Sync and verify (~2 min)
cd /Users/mainguyenbinhtan/Downloads/AKS-SRE-Platform
kubectl -n argocd annotate application flashsale argocd.argoproj.io/refresh=hard --overwrite
kubectl -n argocd get application flashsale -o wide        # → Synced / Healthy
kubectl -n flashsale get job order-migrate -o wide         # → Complete 1/1
kubectl -n flashsale logs job/order-migrate --tail=2       # → "exit code 0"
```

**Total measured wall-clock on 2026-10-21: ≈ 65 minutes** (12:16 → 13:29),
of which the image load was ≈ 13 min, the `payment-service` rebuild + reload
(after the upstream rewrite, §6) ≈ 20 min, and the cluster's own re-creation by
the other actor (before this slice started) was ≈ 1 min.

## 11. Evidence files in this directory

| File | Content |
|---|---|
| `kubectl-nodes.txt` | `kubectl get nodes -o wide` — 3/3 Ready, v1.36.1 |
| `argocd-pods.txt` | `kubectl -n argocd get pods -o wide` — 7/7 Running, 0 restarts |
| `argocd-applications.txt` | `kubectl -n argocd get applications -o wide` — `flashsale Synced / Healthy` |
| `appproject-allowlist.txt` | the live `portfolio` AppProject allowlist |
| `flashsale-pods.txt` | `kubectl -n flashsale get pods -o wide` — the full workload |
| `flashsale-resources.txt` | `kubectl -n flashsale get svc,deploy,sts,job,httproute,scaledobject,pvc -o wide` |
| `order-migrate-job.txt` | `kubectl -n flashsale get job order-migrate -o wide` — `Complete 1/1` |
| `selfheal-reverification-2026-10-21.md` | **the self-heal re-measurement** (later the same day, 13:52–13:54 local): both drift classes re-injected on the restored cluster, with timestamps and verdicts |
| `selfheal-case-a-spec-drift.txt` | case A raw: command, before/after, 1 s poll log, controller-log excerpt, verdict |
| `selfheal-case-b-resource-deletion.txt` | case B raw: command, before/after, 1 s poll log, controller-log excerpt, verdict |
| `selfheal-argocd-controller.log.txt` | the raw `argocd-application-controller` log lines for 06:52–06:54Z |
| `selfheal-application-syncpolicy.txt` | the live Application YAML (syncPolicy / ignoreDifferences / revision) |

## 12. Status of every claim after this run

| Claim | Kind | State |
|---|---|---|
| kind cluster 3/3 Ready, v1.36.1 | **LOCAL_KIND_VERIFIED** | **re-measured 2026-10-21** (this document) |
| Argo CD 7/7 Running, pinned v3.5.5 | **LOCAL_KIND_VERIFIED** | **re-measured 2026-10-21** (this document) |
| `flashsale` Application `Synced` + `Healthy` | **LOCAL_KIND_VERIFIED** | **re-measured 2026-10-21**, final revision `fa08185…` (this document, §6) |
| `order-migrate` PreSync hook `Complete 1/1`, exit 0 | **LOCAL_KIND_VERIFIED** | **re-measured 2026-10-21** (this document) |
| AppProject allowlist refuses a bad destination | **LOCAL_KIND_VERIFIED** | **re-measured 2026-10-21**, 1/1 negative control (this document) |
| spec-drift self-heal | **LOCAL_KIND_VERIFIED (re-measured 2026-10-21)** | **re-measured later the same day** — 21 s drift → Synced (06:52:26Z → 06:52:47Z); see `selfheal-reverification-2026-10-21.md` |
| deletion self-heal | **LOCAL_KIND_VERIFIED (re-measured 2026-10-21)** | **re-measured later the same day** — 17 s delete → `readyReplicas=1` (06:53:37Z → 06:53:54Z); see `selfheal-reverification-2026-10-21.md` |
| extra `metadata.labels` are NOT self-healed | **FINDING, open** | unchanged (§10 of the re-verification document) |
| `legacyapp` deployed | **NOT VERIFIED** | not approved (ADR-015) |
| business E2E / concurrency flow | **NOT VERIFIED** | not re-run |
| `sre-demo-api` pod-level RED metrics | **NOT VERIFIED** | destroyed ACR registry |
| Azure cluster running / billable | **AZURE_CLOUD_LIVE_CONFIRMED** | confirmed read-only 2026-10-21 ~12:2x; teardown prepared, **not executed** |
| `terraform apply` of the AKS foundation | **AZURE_CLOUD_APPLY_NOT_VERIFIED** | no committed apply output |
| `terraform plan` of the AKS foundation | **AZURE_CLOUD_PLAN_VERIFIED** | `terraform-plan.txt` committed |

**Owner for the two open items: P03** — (1) the billable Azure cluster
(`docs/runbooks/azure-teardown-runbook.md`, prepared, not executed), and
(2) the label-drift finding.
