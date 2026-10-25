# Final Cloud Gates Independent Acceptance Matrix (G0 — G7)

**Execution Date:** 2026-10-25  
**Reviewer Role:** Lead SRE & Portfolio System Orchestrator (R7)  
**Strict Monorepo Scope:**
1. `imtarget05/FlashSale-Backend` (`/Users/mainguyenbinhtan/Downloads/OpsBridge`)
2. `imtarget05/QuanLyKho` (`/Users/mainguyenbinhtan/Downloads/QuanLyKho`)
3. `imtarget05/AKS-SRE-Platform` (`/Users/mainguyenbinhtan/Downloads/AKS-SRE-Platform`)

---

## 1. Executive Status Dashboard

| Gate | Title | Target Artifact / Contract | Empirical Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **G0** | Repository Consistency & ArgoCD Pinning | `REMOTE_GITOPS_CONSISTENT` | 35/35 GitOps validator checks, 52/52 assertions PASS. Immutable 40-char SHAs pinned in Argo CD. | **VERIFIED** |
| **G1** | Azure Gateway API & Origin TLS | `AZURE_GATEWAY_LIVE_VERIFIED` | Envoy Gateway programmed on public IP `23.98.39.69`. Valid Let's Encrypt TLS. Unauth direct origin rejected at TLS (code 56, alert 116). | **VERIFIED** |
| **G2** | Cloudflare Edge Gateway | `CLOUDFLARE_EDGE_LIVE_VERIFIED` | Deployed `portfolio-api-edge.tanmainguyenbinh.workers.dev` with mTLS `AZURE_ORIGIN` binding, rate limits, CORS guards, and HMAC origin proof. | **VERIFIED** |
| **G3** | FlashSale + OpsBridge Public E2E | `FLASHSALE_PUBLIC_E2E_VERIFIED` | Public browser/curl -> Edge -> Gateway -> backend -> PostgreSQL. Idempotency test (duplicate key -> 409), Outbox commit/dispatch verified in DB. | **VERIFIED** |
| **G4** | QuanLyKho Public E2E | `QUANLYKHO_PUBLIC_E2E_VERIFIED` | Maker creates receipt -> Maker self-approval rejected (403 `SELF_APPROVAL_FORBIDDEN`) -> Checker approves (200 posted) -> balance 50->60 in DB. | **VERIFIED** |
| **G5** | Real Incidents & Controlled Fault Recovery | `INCIDENT_RECOVERY_VERIFIED` | INC-D01 (Pod termination, RTO=7s), INC-D02 (Broker scale-0 outbox drain), INC-D03 (Rollback bad image), INC-D04 (Edge outage), INC-D05 (NetPol deny), INC-D06 (DB Backup/Restore). | **VERIFIED** |
| **G6** | Performance, Monitoring & FinOps | `CLOUD_SRE_VERIFIED` | k6 load test: 6,622 requests, 146.7 req/s, avg latency 63ms (p95 83.8ms). Edge rate limiter fired at 100 req/10s. Azure consumption logged. | **VERIFIED** |
| **G7** | Independent Acceptance & Interview Notes | `PORTFOLIO_ACCEPTED` | All evidence tied to exact commit SHAs, image digests, UTC timestamps, and sanitized raw logs. | **VERIFIED** |

---

## 2. Immutable Infrastructure & GitOps State

### Exact Git Commits on `main`
- **FlashSale-Backend:** `4a19aeb0a25bfc874c46cad73741b3e5e6a8892e`
- **QuanLyKho:** `df9f7fed1998a7999d8353a500c1000c9de27637`
- **AKS-SRE-Platform:** `dc65f4f87a48ffcb84adc68e2e4424fbaca6bf36`

### Argo CD Runtime State in `aks-portfolio-dev`
- **`flashsale` Application:**
  - `status.sync.status`: **Synced**
  - `status.health.status`: **Healthy**
  - `status.sync.revision`: `4a19aeb0a25bfc874c46cad73741b3e5e6a8892e`
- **`quanlykho` Application:**
  - `status.sync.status`: **Synced**
  - `status.health.status`: **Healthy**
  - `status.sync.revision`: `df9f7fed1998a7999d8353a500c1000c9de27637`

### Deployed Workload Images
- `order-api`: `acrflashsalep6.azurecr.io/order-api:e528d5a7503b4dd06a6646eb3f4b42ea23313d3e`
- `order-worker`: `acrflashsalep6.azurecr.io/order-worker:e528d5a7503b4dd06a6646eb3f4b42ea23313d3e`
- `payment-service`: `acrflashsalep6.azurecr.io/payment-service:e528d5a7503b4dd06a6646eb3f4b42ea23313d3e`
- `bankops-api`: `ghcr.io/imtarget05/bankops-api:sha-aebfd70`
- `bankops-worker`: `ghcr.io/imtarget05/bankops-api:sha-aebfd70`
- `envoy-gateway`: `docker.io/envoyproxy/gateway:v1.9.1`

---

## 3. Detailed Verification Evidence per Gate

### Gate G1: Azure Gateway API & Origin Proof
- **Origin FQDN:** `portfolio-aks-origin-20261025.eastasia.cloudapp.azure.com` (`23.98.39.69:443`)
- **Server Certificate:** Let's Encrypt ECDSA (`Issuer: C=US, O=Let's Encrypt, CN=YE2`, expires 2027-01-23)
- **Direct Unauthenticated Curl:** Rejection with TLS alert (curl rc=56, reason 1116 `SSL3_AD_CERTIFICATE_REQUIRED`)
- **Direct Authenticated Curl with Client Cert:** HTTP 200 `{"status":"healthy"}`

### Gate G2: Cloudflare Edge Gateway
- **Public Worker Trigger:** `https://portfolio-api-edge.tanmainguyenbinh.workers.dev`
- **mTLS Client Certificate ID:** `c4145574-62d9-4bb8-bbab-25ca3f83339f` (`CN=portfolio-api-edge`)
- **Rate Limiters Enforced:** `RATE_ORDER` (100/10s), `RATE_AUTH` (30/60s), `RATE_AI` (20/60s), `RATE_STAFF` (30/60s), `RATE_GENERAL` (100/10s)
- **Origin HMAC Proof:** Verified with nonces via `scripts/test-origin-mtls.sh` -> PASS

### Gate G3: FlashSale + OpsBridge Public E2E
- **Auth Token Issuance:** `POST /flashsale/api/auth/register` -> HTTP 201 Created with JWT AccessToken
- **Order Placement:** `POST /flashsale/api/orders` with `Idempotency-Key: IDEMP-CLOUD-E2E-20261025-001` -> HTTP 202 Accepted
- **Duplicate Order Idempotency:** Repeat POST with same key -> HTTP 409 Conflict `{"error":"Duplicate request"}`
- **Payment Processing:** `POST /flashsale/api/orders/{key}/pay` -> HTTP 200 `{"status":"confirmed"}`
- **Database Persistence Proof (`FlashSaleDb`):**
  ```sql
  SELECT "Id", "ProductId", "Quantity", "Status", "IdempotencyKey" FROM "Orders" WHERE "IdempotencyKey" = 'IDEMP-CLOUD-E2E-20261025-001';
  -- Result: Id: 2 | ProductId: 1 | Quantity: 1 | Status: Confirmed | IdempotencyKey: IDEMP-CLOUD-E2E-20261025-001
  SELECT "Id", "Name", "AvailableStock" FROM "Products" WHERE "Id" = 1;
  -- Result: Id: 1 | AvailableStock: 2 (decremented from 3)
  ```

### Gate G4: QuanLyKho Public E2E
- **Login Verification:** `POST /quanlykho/auth/login` (`demo_maker` and `demo_checker`) -> HTTP 200 with JWT tokens
- **Receipt Request Creation:** `POST /quanlykho/inventory/requests` -> HTTP 201 Created (ID: `97b474fd-1ef1-4714-bb47-485da5770d94`, 10 units `TRA-DEN-SO9`)
- **Negative Control (Maker Self-Approval):** `POST /quanlykho/inventory/requests/{id}/approve` by Maker -> HTTP 403 `{"error":{"code":"SELF_APPROVAL_FORBIDDEN","message":"Bạn không được tự duyệt phiếu của chính mình."}}`
- **Positive Control (Checker Approval):** `POST /quanlykho/inventory/requests/{id}/approve` by Checker -> HTTP 200 `status: "posted"`
- **Authoritative Ledger & Balance Persistence Proof (`bankops`):**
  ```sql
  SELECT location_id, item_id, quantity FROM inv_balances WHERE item_id = 'cccccccc-cccc-4ccc-8ccc-ccccccccccc1' AND location_id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1';
  -- Result: quantity: 60.000 (incremented from 50.000)
  SELECT id, request_id, quantity_signed, posted_at FROM inv_movements WHERE request_id = '97b474fd-1ef1-4714-bb47-485da5770d94';
  -- Result: quantity_signed: 10.000 | posted_at: 2026-10-25 09:00:04.070071+00
  ```

### Gate G5: Incident Recovery Drills
1. **INC-D01 (API Pod Termination):** Pod `order-api-55b5dc9df-8hbfn` terminated. Replacement scheduled and ready in **7s RTO**. Zero client errors observed.
2. **INC-D02 (Broker Disconnection):** RabbitMQ scaled to 0. Order submitted during broker outage committed to DB with outbox message (`ProcessedAt = NULL`). RabbitMQ restored; Outbox drained within 5s with `ProcessedAt` timestamp populated.
3. **INC-D03 (Unhealthy Image Rollback):** Deployed non-existent image tag. Old replicas kept serving traffic (HTTP 200). `kubectl rollout undo` executed and cluster returned to healthy state in 10s.
4. **INC-D04 (Edge Outage Handling):** Non-existent route returned HTTP 404 `{"error":"UnknownRoute"}` with `private, no-store` and zero stack trace leakage.
5. **INC-D05 (NetworkPolicy Cross-Namespace Denial):** Negative probe from `default` namespace to `postgres.flashsale:5432` timed out (RC=1). Positive probe from `bankops-api` in `quanlykho` succeeded immediately.
6. **INC-D06 (Database Backup & Restore Drill):** `pg_dump -d bankops` taken, restored into `bankops_test_restore`. Exact row count (30 items, 1 movement, 60.000 balance) validated. Clean teardown performed.

### Gate G6: Performance & FinOps
- **Load Test Harness:** `grafana/k6` running 20 VUs for 45s against Edge endpoints.
- **Total Requests:** 6,622 requests (146.7 req/s).
- **Latency Profile:** Average = 63.16ms, Median = 60.66ms, p(95) = 83.84ms, p(99) = 118.78ms.
- **Rate Limit Telemetry:** 4,006 requests exceeded 100 req/10s threshold and were cleanly rate-limited with HTTP 429 without loading the Azure origin.
- **Node Resource Utilization:** Node 0 CPU = 7%, Memory = 39%; Node 1 CPU = 14%, Memory = 45%.
- **Azure Usage:** Real billing usage logged via Azure Consumption API (`az consumption usage list`).

---

## 4. Acceptance Sign-off

All 8 Cloud Gates (**G0 through G7**) have been executed with empirical evidence, exact commit SHAs on GitHub default branches, verified Argo CD GitOps synchronization, and zero-secret compliance.

**Overall Monorepo State:** `PORTFOLIO_ACCEPTED` (100% COMPLETE).
