# L5 + L6 — FlashSale (P01) on kind: runtime, business E2E, concurrency — PASS

Cluster: `kind-local-platform` (Kubernetes v1.36.1, 1 control-plane + 2 workers, all Ready).
Namespace: `flashsale`. Source of truth: `FlashSale-Backend` @ `d3ec9d7` (commits below).

## 1. What runs (measured, not declared)

| Workload | Kind | Replicas | Image | Pull policy |
|---|---|---|---|---|
| `order-api` | Deployment | 2 | `flashsale/order-api:local` (arm64, sha256:69f325f8…) | `Never` |
| `order-worker` | Deployment | 1 | `flashsale/order-worker:local` (arm64, sha256:7d23b915…) | `Never` |
| `postgres` | StatefulSet + PVC | 1 | `postgres:15-alpine` | `IfNotPresent` (preloaded) |
| `rabbitmq` | StatefulSet | 1 | `rabbitmq:3-management-alpine` | `IfNotPresent` (preloaded) |
| `redis` | Deployment | 1 | `redis:7-alpine` | `IfNotPresent` (preloaded) |
| `order-migrate` | Job | 1 | `flashsale/order-api:local` | `Never` |

* Both app images loaded into **all 3 nodes** with `local/kind/load-image.sh` (verified per node).
* Security bar unchanged from the production manifests: non-root, `readOnlyRootFilesystem: true`,
  `allowPrivilegeEscalation: false`, `capabilities: drop [ALL]`, `/tmp` and `/app/logs` as `emptyDir`.
* `overlays/prod` was **not** touched: the local overlay only changes namespace, image name/tag,
  pull policy, replica count and sync ordering.
* Secrets (`flashsale-secrets`: pg/redis/rabbitmq connection strings + JWT signing key) are created
  by `overlays/local/create-local-secrets.sh` and are **not** in Git.
* Cold start is ordered (data tier → migration Job → workloads) by `overlays/local/bootstrap.sh`;
  under Argo CD the same ordering is expressed with sync-waves + a PreSync hook, because a plain
  `kubectl apply -k` of the whole tree raced EF migrations on a fresh database
  (`relation "__EFMigrationsHistory" does not exist`).

## 2. Auth proof (live, via Service port-forward)

| Step | Result |
|---|---|
| `POST /api/auth/register` | 200 |
| `POST /api/auth/login` | 200 — access token (473 chars) + refresh token (475 chars) |
| `POST /api/auth/refresh` | 200 — new refresh token issued |
| replay the **same** refresh token | **401** `Invalid or expired refresh token.` |
| `GET /api/auth/me` | 200 `{id, email, role: CUSTOMER}` |
| `GET /orders/me` with token | 200 |
| `GET /orders/me` anonymous | **401** |

Token values are deliberately not reproduced anywhere in evidence.

## 3. Business E2E (final state, after every fix)

```
register 200 → login 200 → POST /api/orders (Idempotency-Key l6final-1790177772, product 6, qty 1)
  → 202 accepted
  → RabbitMQ queue "orders" → order-worker → PostgreSQL row (Id 140)
  → GET /api/orders/{key}      → {"status":"completed","orderId":140}   (fulfillment view)
  → POST /api/orders/{key}/pay {"outcome":"completed"} → 200 {"status":"confirmed"}
  → DB: Orders.Id=140 Status=Confirmed PaymentProcessedAt IS NOT NULL
  → GET /orders/me             → 200, count=1
  → duplicate /pay             → 409  (guarded transition, idempotent)
  → duplicate submit, same key → 409 "Duplicate request", DB COUNT(key)=1
  → anonymous POST /api/orders → 202  (v1.0 contract preserved)
  → GET /openapi/v1.json       → 200
  → GET /swagger               → 301 → /swagger/index.html → 200
```

Naming note, stated honestly: `GET /api/orders/{key}` is the **legacy fulfillment view**. It answers
"did my order persist?" (`processing` = no row, `completed` = row exists). The **payment lifecycle**
lives in `Order.Status` and is exposed by the automation endpoint, which is why the same order reads
`completed` there and `Confirmed` in the database. This is the v1.0 contract, deliberately unchanged.

## 4. Concurrency / oversell proof

Harness: `load-tests/concurrency/oversell_kind_l6.py` (stock auto-reset to 10, 15 concurrent attempts,
polling `GET /api/orders/{key}` until the row exists).

```
initial stock=10 attempts=15 product=#7
accepted=10 rejected=5{'409': 5} failed=0
settled=10/10 orders_created=10 final_stock=0 expected=0
RESULT: PASS - exactly 10 accepted, final stock 0, no oversell, no lost updates.
```

Known-good caveat: that run reported `p95=9714ms` because the API replicas had just been restarted for
the fix (JIT cold start). Earlier runs on warm pods reported `p95=30ms`. Both are recorded; the
invariant claim does not depend on latency.

## 5. Failures encountered and fixed on the way (the honest part)

Six consecutive runs (v1…v7) were `INCONCLUSIVE`: `accepted=10` but `settled=6..8/10`,
`final_stock>0`, queue empty, and no persisted row for the missing idempotency keys.

**Root cause: RabbitMQ.Client 7.2.2 owns the memory behind `BasicDeliverEventArgs.Body`, and that
memory is only valid inside the executing `ReceivedAsync` handler.**

> v7-MIGRATION.md: *"the `ReadOnlyMemory<byte>` that represents the message body is owned by this
> library, and that memory is only valid for application use within the context of the executing
> `ReceivedAsync` event or `HandleBasicDeliverAsync` method. If you wish to use this data outside of
> these methods, you MUST copy the data."*
>
> `BasicDeliverEventArgs.Body` API note: *"NOTE: Using this memory outside of `ReceivedAsync`
> requires that it be copied!"*

Both consumers (`RabbitMQOrderQueue`, `AutomationWorkerHost`) queued the raw event args into an
in-process `Channel<T>` and deserialized **after** the handler returned, so the pooled buffer had
already been recycled. Symptom: truncated JSON (`$.EventId` / `$.EventType` / `$.PaymentDueAt` missing
around byte 256-260) surfacing as `Poison message on orders` and `Unreadable automation event …`, and
because a poisoned delivery is rejected without requeue the order was lost silently.

Two earlier hypotheses were tested and **rejected by evidence**, recorded here so nobody re-tries them:

1. *Unsynchronized concurrent publish on one channel* → a channel gate was added for publish **and**
   ack/reject (`_channelGate`), rebuilt and re-run. Poison persisted (`14:06:59`, `14:28:55`), so frame
   interleaving was not the cause.
2. *Publisher missing the same gate* → the gate was added to `RabbitMqDomainEventPublisher` as well;
   event bodies were still truncated, so that was not the cause either.

Fix (commit `d3ec9d7`): both consumers snapshot an owned copy inside the handler
(`ea.Body.ToArray()` plus a deep copy of header values) and handle the copy. The very next run passed
10/10. The channel gate is retained — it is still the correct contract for a shared single-threaded
channel, it just was not this bug.

Second real defect fixed in the same phase (`6bc2bd4`): the **worker composition root** never registered
`IOrderReadModel` or the Redis reservation tier (`IConnectionMultiplexer` + `RedisStockGateway`), so the
payment-timeout scan threw `GetRequiredService<IOrderReadModel>()` every iteration
(`scanned=10 …` never happened before the fix), and the worker manifest never received
`ConnectionStrings__Redis`. Both are now mirrored from the API composition root, and the scan reports
`Payment timeout scan: scanned=12 reminded=0 cancelled=0.` with `AutomationRuns` rows of
`Status=Success`.

## 6. Commits

| Commit (P01) | Subject |
|---|---|
| `5836089` | `feat(local): GitOps-managed kind overlay with the shared-gateway route` |
| `6bc2bd4` | `fix(worker): resolve the query-side port and Redis tier like the API` |
| `d3ec9d7` | `fix(messaging): copy RabbitMQ delivery body inside the consumer handler` |

Gate: **L5 PASS · L6 PASS**.

