# Historical AKS validation — cluster deleted

**Evidence status:** `AZURE_K8S_LIVE_VERIFIED` for the historical control-plane
observation; `AZURE_CLOUD_APPLY_NOT_VERIFIED` for Terraform apply because no
command output from that apply was committed. These labels describe different
claims. The cluster `aks-portfolio-dev` was deleted on **2026-10-21**.

| Observation | Evidence | Limit |
|---|---|---|
| AKS control plane, one Ready system node at Kubernetes v1.36.4 | [Read-only Azure re-verification](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/evidence/live-aks-azure-2026-10-21/aks-azure-evidence.md) | Point-in-time observation; cluster no longer exists |
| System/user pool placement, private ACR digest pull, scoped Workload Identity token exchange | [Phase 7A final report](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/evidence/phase7a/phase7a-FINAL-PASS.md) | Earlier transient run; proof identities/pools were deleted |
| Saved Terraform plan | [Plan artifact](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/evidence/live-aks-2026-10-20/terraform-plan.txt) | Does not establish that apply command ran |
| Teardown | [Runbook execution transcript](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/runbooks/azure-teardown-runbook.md) | Historical completion, not a live resource check today |

No Argo CD, Gateway API, Prometheus/Grafana runtime, autoscaler scale-out,
NetworkPolicy deny probe, or production SLO history is proven by this Azure
run. The local [architecture page](../architecture/overview.md) names the
separate kind proof.
