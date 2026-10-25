# AKS user-pool autoscaling proof

Status: procedure only. No HPA or node scale event has been observed at this checkout. This proof belongs to ADR-014's transient **Profile A**; do not run it alongside the observability load profile.

## Bound and prerequisites

- Terraform's system pool stays fixed at one `Standard_D2s_v6` node. Enable only the user pool's cluster autoscaler with `min_nodes=1`, `max_nodes=3`. At this SKU, the declared upper bound is 2 + (3 × 2) = **8 vCPU**, leaving 2 vCPU below the recorded 10-vCPU regional quota. Recheck live quota and current usage before each run; these figures are a configuration bound, not measured spare capacity today.
- AKS owns the autoscaler process and its cluster-wide default profile. This repo configures the user node pool through Terraform. It must not install `kube-system/cluster-autoscaler-status` or an invented autoscaler PDB; that ConfigMap is observed status, not an AKS configuration API. Custom tuning, if justified by a live baseline, belongs in the Terraform `azurerm_kubernetes_cluster.auto_scaler_profile` block after a separate plan review.
- Reconcile remote Terraform state and review the saved plan before any apply. Stop if it replaces the cluster/node pool, changes another workload, or exceeds the current quota/cost budget. `enable_workload_pool=true` and `workload_pool_autoscaling.enabled=true` must be explicit. Do not run `terraform apply` from the module directory.
- The validation overlay currently points to a destroyed ACR. Rebuild `app/sre-demo-api`, publish to a reachable registry, and replace the image with an immutable digest before deploying the overlay. Verify pull, readiness, Metrics Server and both objects: `kubectl -n sre-platform get deploy,hpa,pdb sre-demo-api`.
- Record UTC time, Git SHA, Terraform plan fingerprint, AKS context, image digest, initial node and replica counts, quota and cost estimate. Keep credentials and raw Terraform plans out of Git.

## HPA proof

1. Render `kubectl kustomize deploy/overlays/validation`. Check that HPA targets Deployment `sre-demo-api`, min=2/max=4, and the container has a CPU request. Diff and deploy only after review.
2. Start read-only snapshots with `python3 scripts/log_scale_events.py --context aks-portfolio-dev --namespace sre-platform --samples 30 --interval-seconds 30 --output .local/autoscale-evidence.jsonl`. The script queries actual HPA status, user nodes and Kubernetes events; each JSON line records the observation time in UTC. It does not synthesize a scale event. Keep the output local until sanitized.
3. Port-forward `svc/sre-demo-api` to the workstation. For a bounded 90-second window, send concurrent requests to `/api/work?n=200000`; stop if error rate or latency harms other workloads. The endpoint caps `n` at 200000. Capture Deployment Ready replicas, pod CPU from `kubectl top pods`, and client counts alongside the JSONL snapshots. The target proof is observed `desiredReplicas > 2`, Ready replicas follow, then return to 2 after load ends and the five-minute downscale stabilization window passes. Do not infer scale from a rendered manifest.

## Node proof

1. Capture `kubectl get nodes -l agentpool=work -o wide`, `kubectl -n sre-platform get pods -o wide`, and `kubectl -n sre-platform get events --sort-by=.lastTimestamp` before inducing scheduling pressure. Confirm the `work` pool has `autoScalingEnabled=true`, min=1 and max=3 in the live AKS node-pool configuration.
2. In the validation namespace only, create a temporary, non-serving proof Deployment using a **reviewed immutable image digest** and `nodeSelector: {workload: portfolio}`. Set two replicas, each with CPU request `1500m` and memory request `512Mi`; keep the command idle and give it a short, recorded cleanup deadline. One D2s_v6 user node should not fit both requests after system DaemonSets, so a Pending pod can trigger AKS cluster autoscaler. If no pod is Pending, record that result and adjust the proof requests only after recalculating allocatable capacity and the 8-vCPU envelope. Never force scale by editing the system pool.
3. Compare consecutive JSONL snapshots for the Pending/scheduling event, user-pool node count increase, new node Ready, and later scale-down. Also capture both proof pods Ready and live AKS node-pool/VMSS counts with UTC timestamps. Then delete the proof Deployment, observe pods terminate, and wait for node count to return to the configured minimum; AKS scale-down can take minutes. Save before/after Azure usage and billing evidence. If scale-out is blocked by quota, record a failed proof instead of marking the capability complete. Do not use a fabricated Prometheus counter as scale evidence.

## Rollback and acceptance

Delete the temporary proof Deployment first and stop the load client. Revert the validation overlay to its reviewed digest. If an autoscaler plan causes unexpected behavior, review a Terraform plan that sets `workload_pool_autoscaling.enabled=false` and fixed user count 1 before applying; do not manually edit VMSS capacity behind AKS. Preserve evidence of the fault and the recovery. A result is accepted only when HPA scale-out/down and node scale-out/down are both observed at the exact release SHA with UTC logs, image digest, quota check and independent review.

Provider parameter reference: [Terraform AzureRM node pool](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/kubernetes_cluster_node_pool). Runtime behavior reference: [Microsoft AKS cluster autoscaler](https://learn.microsoft.com/en-us/azure/aks/cluster-autoscaler).
