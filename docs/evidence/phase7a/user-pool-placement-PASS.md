# 7A.2 Proof 1 — User Pool Isolation — PASS (2026-09-21)

Source commit (7A.1 freeze): `e66cd0c`. Cluster `aks-portfolio-dev` started
16:16:59Z; both `sys` nodes Ready (v1.36.4) before proceeding.

## Fresh quota gate (pre-pool, all PASS)

- Regional cores: **8/10** (2 free ≥ 2) · Dsv6 family: **8/10** (2 free ≥ 2)
- `Standard_D2s_v6`: `Restrictions=[]`, 2 vCPU → eligible, no SKU switch.

## Pool creation (Terraform saved plan `.local/phase7a2-workpool.tfplan`, gitignored)

- Plan: **1 add / 1 change / 0 destroy**. Add = `azurerm_kubernetes_cluster_node_pool.work[0]`
  (User, 1 node, `Standard_D2s_v6`, Regular, autoscaling OFF, Spot OFF).
- The 1 in-place change = documented provider-block null normalization on the
  cluster (`upgrade_settings` → null); no replacement, no destroy (verified
  `must be replaced` count = 0). System pool untouched.
- Apply exact plan: 1 added. State: pool `work` Succeeded; nodes 2 sys + 1 user,
  all Ready (`aks-work-…-vmss000000`, v1.36.4).

## Placement proof

- Actual node labels (not assumed): work node carries
  `kubernetes.azure.com/agentpool=work` + `kubernetes.azure.com/mode=user`;
  sys nodes carry `agentpool=sys` + `mode=system`.
- Namespace `phase7a-proof` created. Pod `placement-probe`
  (`registry.k8s.io/pause:3.10`) with
  `nodeSelector: {kubernetes.azure.com/agentpool: work}` →
  **1/1 Running on `aks-work-…-vmss000000`** (work pool, NOT sys).
- No proof workload scheduled on `sys`.

## Incidents

- First probe image (`mcr.microsoft.com/oss/nginx/nginx:1.9.3`) → `NotFound`
  (wrong tag; registry itself reachable). Repulled strategy: use `pause:3.10`
  for pure placement proof. No impact on gates.

## Cleanup (see FINAL-PASS for full chain)

Pool destroyed same session via saved plan (destroy strictly
`azurerm_kubernetes_cluster_node_pool.work[0]`); only `sys` remains, quota back
8/10, cluster stopped. Namespace deleted (Step 15).

## Gate

User pool actually created ✅ · workload on user pool ✅ · nothing on sys ✅.
