# FinOps boundary for transient AKS proof

The AKS validation cluster was **deleted on 2026-10-21**. A monthly estimate
for a continuously running cluster would misstate this project's current cost.
The recorded 10-vCPU regional quota is a point-in-time capacity measurement,
not an Azure invoice or a guarantee that today's quota is unchanged.

The validation design uses one 2-vCPU system node and up to three 2-vCPU user
nodes, leaving two vCPU under the measured quota. Autoscaler and full
observability are separate experiment profiles under that envelope; they have
not been proven together on AKS.

For any future Azure run: remeasure quota and price, review a saved Terraform
plan and explicit approval, record start/end and resources, capture runtime
proof, then follow the
[teardown runbook](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/runbooks/azure-teardown-runbook.md).
Budget alerts warn; they do not stop spend automatically. Do not infer actual
cost from a VM SKU table without Cost Management data.
