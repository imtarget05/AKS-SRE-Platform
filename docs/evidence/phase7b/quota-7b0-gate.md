# Phase 7B.0 Quota Gate — BLOCKED (2026-09-21, API path)

Source: user directive 7B.0 (quota 10→16 before any 7B.1 pool creation).

## Fresh quota (live)

- Cluster Stopped (1.36.4). `az vm list-usage eastasia`: `cores` **0/10**,
  `StandardDsv6Family` **0/10** (deallocated while stopped).
- Running math: sys 8 + persistent work 2 = **10/10, zero headroom** → increase
  required. `Standard_D2s_v6`: `Restrictions=[]` (eligible, no SKU change).

## API attempt (FAILED — manual path required)

- Registered `Microsoft.Quota` RP (was unregistered; registration is harmless
  control-plane metadata, no cost/resources).
- Quota API confirms current limits: `cores` = 10, `StandardDsv6Family` = 10.
- `az quota update` → 16 for **both** `StandardDsv6Family` and `cores`:
  **ERROR `ContactSupport` / "Request failed."** (2 request IDs recorded in
  `az quota request list`, both failed). Read path works; auto-approve does
  not on this subscription.

## Exact manual steps (portal)

1. Azure Portal → search **Quotas** → select subscription **Azure subscription 1**.
2. Provider **Compute**, region **East Asia**.
3. Edit quota: **Total Regional vCPUs** (`cores`) 10 → **16** → submit.
4. Edit quota: **Standard Dsv6 Family vCPUs** (`StandardDsv6Family`) 10 → **16** → submit.
5. If the portal marks either as "not eligible for increase" / requires support:
   Help + support → New support request → Issue type **Service and subscription
   limits (quotas)** → Quota type **Compute-VM (cores-vCPUs)**, location East
   Asia, details: Total Regional vCPUs 10→16; Standard Dsv6 Family 10→16;
   business justification: portfolio AKS platform bootstrap (system 8 + user 2
   = 10/16, headroom 6 for retry/maintenance).
6. Re-verify live: `az vm list-usage -l eastasia` (usage 0/10→0/16 while
   stopped) + `az quota show` limits 16/16 before authorizing 7B.1.

Alternative if increase is denied (NOT auto-applied): keep quota 10 and
re-scope 7B to a smaller footprint as a new explicit decision — do NOT shrink
the sys pool or switch SKU silently.

## Impact

No VM/node created, no cost incurred, no region/SKU changed. Quota limit
itself costs $0. **7B.1 NOT authorized until limits read ≥16/≥16 live.**
