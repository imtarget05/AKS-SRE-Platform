# Azure cutover baseline — 2026-10-24

Scope: read-only Azure and Kubernetes inspection. The Platform code branch at
the time of capture was `8d7eda8e7ecdc83e4d8868027416c8e0ba52e142`.
The code checks and GitHub CI are separate from these runtime observations.

| Command / context | Observed result | Meaning |
| --- | --- | --- |
| `az aks list` | `aks-portfolio-dev`, `eastasia`, Running/Succeeded | Cluster exists; no workload readiness inferred. |
| `az vmss list -g MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia` | One `Standard_D2s_v6` node | Cloud spend is ongoing while this node runs; no monthly cost estimate is claimed. |
| `az postgres flexible-server list` | `[]` | No managed PostgreSQL server in the active subscription. |
| `az mysql flexible-server list` | `[]` | No managed MySQL server in the active subscription. |
| `az network public-ip list` | One AKS-managed address `4.144.27.45`, no DNS FQDN | This is not the reviewed static, certificate-backed origin. |
| `kubectl --context aks-portfolio-dev get gatewayclass` | Resource type not installed | Gateway API/Envoy north-south path is absent on AKS. |
| `kubectl --context aks-portfolio-dev get applications -n argocd` | `flashsale` and `quanlykho`: OutOfSync/Missing | Existing Argo objects do not prove a running workload. |
| `kubectl --context aks-portfolio-dev get pods -n flashsale` and `-n quanlykho` | No resources found | Neither workload is deployed on AKS at this capture. |
| `python3 scripts/check-cloud-cutover.py` | Exit 1; six blockers (local overlay, moving ref, automated sync for each app) | Cloud promotion is intentionally blocked. |

The default `kubectl` context on this machine is `kind-local-platform`.
Commands without `--context aks-portfolio-dev` describe Kind and must never
be used as AKS evidence. The Kind Gateway/HTTPRoutes are present and healthy,
but do not change the AKS observations above.

Next required proof before spending on cutover: identify Terraform remote state
owner and Azure budget/quota; create reviewed managed DBs, public IP/DNS and
certificates; install Gateway API/Envoy; render and server-validate the HTTPS
Gateway; show a failed TLS handshake without client cert and a successful
Worker request; pin immutable workload images and Git revisions; test
migration, rollback, restore and actual cost. No production-readiness or
USD 100/month claim is made by this baseline.
