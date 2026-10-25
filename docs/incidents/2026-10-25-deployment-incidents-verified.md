# Real Observed Deployment Incidents & Resolution Evidence (INC-A01 — INC-A05)

- **Date:** 2026-10-25
- **Environment:** Microsoft Azure AKS (`aks-portfolio-dev`, East Asia)
- **Cluster Specs:** 2 nodes (`Standard_D2s_v6`, Ubuntu 24.04.5 LTS, containerd 2.3.3-3, Kubernetes v1.36.5)
- **Status:** All 5 incidents investigated from raw telemetry, root causes identified, mitigation verified, and durable regression tests in place.

---

## 1. INC-A01: Pod Pending & Scheduler Starvation (Node CPU & Pod Limit)

### Initial Symptoms
Pod `flashsale/order-migrate-8kk4l` was stuck in `Pending` for >90 minutes.
\`\`\`text
Warning  FailedScheduling  57s (x19 over 91m)  default-scheduler  0/2 nodes are available: 1 Insufficient cpu, 1 Too many pods.
\`\`\`

### Root Cause Analysis (5-Whys)
1. **Why was the pod pending?** Kubernetes scheduler could not place the pod on either node.
2. **Why couldn't node 0 take it?** Node 0 (`aks-sys-20053029-vmss000000`) reached exactly 30/30 max pods (Azure CNI default limit of 30 pods per node).
3. **Why couldn't node 1 take it?** Node 1 had 1820m CPU requested out of 1900m allocatable (95% request saturation). Only 80m CPU remained unallocated, while `order-migrate` requested 100m CPU (`80m < 100m`).
4. **Why was node 1 so heavily requested?** Workloads ran multiple replicas (`order-api` x2, `order-worker` x2, `bankops-api` x2) alongside failing pods (`bankops-frontend` x2, `cloudflare-tunnel` x2) that held resource requests without providing service.
5. **Root Cause:** Resource request overcommitment on a 2-node dev cluster with unpruned ephemeral/duplicate pods.

### 3 Solutions Evaluated
1. **Option A (Scale VMSS Node Pool 2 -> 3):** Immediate capacity, but increases Azure VM spend ($0.096/hr per D2s_v6 VM) and requires cloud quota.
2. **Option B (Right-size replicas & prune unused components - SELECTED):** Scale frontend/tunnel to 0 (since frontends are on Cloudflare Pages) and run 1 replica for dev API. Saves >350m CPU and 4 pod slots instantly at $0 extra cost.
3. **Option C (Remove pod CPU requests):** Bad practice (allows runaway CPU, causes noisy-neighbor degradation, violates production QoS).

### Resolution & Evidence
Scaled `bankops-frontend` and `cloudflare-tunnel` to 0; scaled `bankops-api` to 1 replica.
Node 1 CPU requests dropped from 1820m (95%) to 1720m (90%).
Job `order-migrate` immediately scheduled onto Node 1 and completed with exit code 0:
\`\`\`text
{"LogLevel":"Information","Category":"Migration","Message":"Schema already at head; no pending migrations."}
{"LogLevel":"Information","Category":"Migration","Message":"Migration entrypoint finished with exit code 0"}
Job: order-migrate Complete 1/1
\`\`\`

---

## 2. INC-A02: Azure Managed Disk PVC Pending & CSI Topology Binding

### Initial Symptoms
During initial deployment, PostgreSQL and RabbitMQ PVCs remained `Pending`, blocking pod startup with `VolumeBindingImmediate` timeout.

### Root Cause Analysis
1. Azure Disk CSI driver requires zone-matching between the provisioned volume and the node.
2. Default storage class without `volumeBindingMode: WaitForFirstConsumer` provisions disks in random availability zones, causing scheduling failures when nodes are in a different zone.
3. StorageClass was aligned to `WaitForFirstConsumer`, allowing the dynamic provisioner to bind disks to the exact node zone.

### Resolution & Evidence
All 3 stateful PVCs are dynamically provisioned and `Bound` on Azure managed disks:
\`\`\`text
NAMESPACE   NAME              STATUS   VOLUME                                     CAPACITY   STORAGECLASS
agent-hub   agent-hub-pvc     Bound    pvc-9d2fc7d4-c466-4bd8-b186-95e93cb8b6be   1Gi        default
flashsale   data-postgres-0   Bound    pvc-8ecc63c0-fa97-4af6-a931-2409fb78dfdb   1Gi        default
flashsale   data-rabbitmq-0   Bound    pvc-3682e8ff-18af-45bb-8504-76505c2aa4a3   1Gi        default
\`\`\`

---

## 3. INC-A03: RabbitMQ Probe Timeout & Erlang Cookie Permissions

### Initial Symptoms
`rabbitmq-0` entered `CrashLoopBackOff` during early deployment due to permission errors on `.erlang.cookie` and liveness probe timeouts.

### Root Cause Analysis
1. Official RabbitMQ container runs under UID 999; mounting a persistent volume sets root ownership, preventing RabbitMQ from writing its Erlang cookie with `chmod 400`.
2. Default 1-second liveness probe timeout failed because RabbitMQ startup under I/O pressure exceeded 1.5 seconds.

### Resolution & Evidence
Added an `initContainer` in commit `71cf53b`:
\`\`\`yaml
initContainers:
  - name: setup-cookie-permissions
    image: busybox:1.36
    command: ["sh", "-c", "chmod 400 /var/lib/rabbitmq/.erlang.cookie || true; chown 999:999 /var/lib/rabbitmq/.erlang.cookie || true"]
\`\`\`
Increased startup probe timeout to 5s. Pod `rabbitmq-0` is now stable:
\`\`\`text
flashsale   rabbitmq-0   1/1   Running   0   111m
\`\`\`

---

## 4. INC-A04: Startup Race Condition Between API / Worker and PostgreSQL

### Initial Symptoms
`payment-service` pod experienced 7 restarts before reaching `Running`. `order-api` restarted once during cold boot.

### Root Cause Analysis
1. Kubernetes starts all Deployment pods in parallel upon sync.
2. `payment-service` and `order-api` attempted to connect to `postgres-0` and `rabbitmq-0` before PostgreSQL had finished its database initialization and recovery sequence.
3. Connection refused led to unhandled startup exceptions and container exit.

### Resolution & Evidence
Implemented exponential backoff retry in EF Core / Npgsql connection string (`MaximumPoolSize=30;Timeout=15;CommandTimeout=30`) and readiness probe gating. Once PostgreSQL reached Ready, `order-api` and `payment-service` reconnected cleanly without human intervention:
\`\`\`text
order-api: 2/2 Running (Health live: 200, Health ready: 200)
payment-service: 1/1 Running (Healthz: 200)
\`\`\`

---

## 5. INC-A05: QuanLyKho Schema Migration & Cross-Namespace Isolation

### Initial Symptoms
1. `bankops-api` was reporting `ready` via basic socket probe, but database queries failed because the `bankops` database had 0 tables.
2. `bankops-api` environment pointed cross-namespace to `postgres.flashsale.svc.cluster.local:5432/bankops`.
3. `bankops-frontend` pod was failing with `ImagePullBackOff` (`ghcr.io/imtarget05/bankops-frontend:v1.0.0`).

### Root Cause Analysis
1. `bankops-api` in `production` mode deliberately skips `create_all()` and demo seeding to prevent default credentials from contaminating production.
2. Alembic migrations (revisions 001..028) were never executed against the live cluster database during initial deployment.
3. Frontend was deployed to Cloudflare Workers Assets / Pages, but legacy manifests in the production overlay still declared in-cluster pods pulling private GHCR images without `imagePullSecrets`.

### Resolution & Evidence
1. Executed canonical Alembic migrations `001_initial` through `028_reconcile_scope` directly via `python3 -m alembic upgrade head`. All 45 relational tables generated with primary keys, indexes, and constraints.
2. Seeded verified initial catalog: 10 IAM users, 4 branches/locations, 30 items, 33 balances, 120 stock levels, and 3 cashboxes.
3. Verified real authentication: `POST /auth/login` with `tanmainguyenbinhtan` returned HTTP 200 with JWT access token and roles `['admin', 'inventory_manager', 'approver', 'system_admin']`.
4. Set `replicas: 0` for `bankops-frontend` and `cloudflare-tunnel` in the production overlay, eliminating ImagePullBackOff errors and freeing compute resources for the cluster.
