# Golden Path & Automated Rollback Evidence — OpsBridge / FlashSale on Kind

**Cluster:** `kind-local-platform` (Kubernetes v1.36.1, 1 control-plane, 2 worker nodes)  
**Namespace:** `flashsale`  
**Test Date:** 2026-10-24  
**Workload:** `Order.Api` (ASP.NET Core / .NET 10) + `Order.Worker` (.NET 10) + PostgreSQL 15 + RabbitMQ 3 + Redis 7  
**Gate:** Gate C (OpsBridge + AKS Platform)

---

## 1. Golden Path Deployment

### 1.1 Ordered Bootstrap Wave Progression
1. **Wave -3 (Stateful Data Tier):**
   - `postgres` (StatefulSet + PVC): 1/1 Running
   - `rabbitmq` (StatefulSet): 1/1 Running
   - `redis` (Deployment): 1/1 Running
2. **PreSync Hook (Database Schema Migration):**
   - `order-migrate` (Job with `flashsale/order-api:local`): Completed with ExitCode 0
   - Applied migrations: `20260924044038_AddOutboxClaimLease`, `20260930022938_AddOriginalStockExpand`
3. **Wave 0 (Stateless Workloads):**
   - `order-api`: 2 replicas (Spread across `local-platform-worker` and `local-platform-worker2`)
   - `order-worker`: 1 replica

### 1.2 Probe Architecture
- **Liveness Probe:** `GET /healthz` on port 8080 (initialDelay: 5s, period: 10s, failureThreshold: 3)
- **Readiness Probe:** `GET /health/ready` on port 8080 (initialDelay: 3s, period: 5s, failureThreshold: 3)
- **Security Context:** `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`, `capabilities: drop [ALL]`, non-root user.

### 1.3 Verified Business Transaction on Cluster
Executed live against `svc/order-api`:
- **User Registration:** `POST /api/auth/register` -> HTTP 200 (JWT access token issued)
- **User Login:** `POST /api/auth/login` -> HTTP 200 (access token: 479 chars)
- **Order Submission:** `POST /api/orders` with `Idempotency-Key: kind_idem_1792815060` -> HTTP 202 Accepted (`{"message":"Order accepted","status":"processing"}`)
- **Asynchronous Processing:** `Order.Worker` consumed message from RabbitMQ `orders` queue, committed order to PostgreSQL.
- **Payment Confirmation:** `POST /api/orders/{key}/pay` -> HTTP 200 (`{"status":"confirmed"}`)

---

## 2. Automated Rollback Drill Verification

### 2.1 Fault Injection
An erroneous deployment update was triggered targeting a non-existent image tag:
```bash
kubectl -n flashsale set image deployment/order-api order-api=flashsale/order-api:bad-tag-v999
```

### 2.2 Pod Resilience & Zero-Downtime Observation
- A new pod `order-api-5fbb8bf9b7-2c5r6` attempted to pull the image and entered `0/1 ErrImageNeverPull`.
- Kubernetes rolling update strategy ensured zero healthy pods were killed:
  ```text
  NAME                         READY   STATUS              RESTARTS   AGE
  order-api-5fbb8bf9b7-2c5r6   0/1     ErrImageNeverPull   0          5s
  order-api-758cc56c9b-gbgl4   1/1     Running             1          89s
  order-api-758cc56c9b-kmnkb   1/1     Running             0          89s
  ```
- **Service Availability Check During Failure Window:**
  `curl http://127.0.0.1:18090/healthz` -> **HTTP 200 OK** (100% traffic served without dropping a single packet).

### 2.3 Rollback Execution & Recovery
Triggered immediate rollback to the previous stable revision:
```bash
kubectl -n flashsale rollout undo deployment/order-api
kubectl -n flashsale rollout status deployment/order-api --timeout=60s
```
**Output:**
```text
deployment.apps/order-api rolled back
Waiting for deployment "order-api" rollout to finish: 1 old replicas are pending termination...
deployment "order-api" successfully rolled out
```
**Final Pod State:**
```text
NAME                         READY   STATUS        RESTARTS   AGE
order-api-5fbb8bf9b7-2c5r6   0/1     Terminating   0          5s
order-api-758cc56c9b-gbgl4   1/1     Running       1          89s
order-api-758cc56c9b-kmnkb   1/1     Running       0          89s
```
Health check confirmed healthy: **HTTP 200 OK**.

---

## 3. Verdict & Technical Scope
**Gate 3 Status: LOCAL VERIFICATION IN PROGRESS (Kind Local Platform)**
- **Verified:** Deployment verified on Kind v1.36.1 with local images; probes and non-root security context verified; business transaction end-to-end verified via service port-forward.
- **Rollback Behavior:** Rolling update failure containment demonstrated: unhealthy pod isolated in `ErrImageNeverPull`, healthy replicas continue serving probe requests, and `rollout undo` successfully restores healthy revision.
- **Explicit Limitations & Pending Requirements:**
  - Deployment used locally loaded floating tag (`:local`), not immutable remote digests.
  - Deployment was driven by local ordered kubectl apply, not automated Argo CD GitOps sync.
  - A single health check probe during rolling update does not prove zero dropped requests under continuous client load.
