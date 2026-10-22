# Production SRE Runbooks Catalog

> **Scope**: AKS Cloud-Native Reliability Platform  
> **Operational Matrix**: See [Master SLI/SLO Index](../operations/SLI_SLO_RUNBOOK_INDEX.md) for full mapping.

---

## Runbooks Index

| Runbook File | Primary Objective | Severity | Trigger |
|---|---|---|---|
| [runbook-sli-slo-error-budget-burn.md](runbook-sli-slo-error-budget-burn.md) | Multi-window burn rate alert remediation (Google SRE 14.4x/6.0x) | P1 / P2 | Prometheus `SLOHighErrorRateBurn` |
| [runbook-pdb-node-drain-maintenance.md](runbook-pdb-node-drain-maintenance.md) | Zero-downtime node pool drain operations with PodDisruptionBudget | P2 | Planned node OS upgrade / maintenance |
| [runbook-network-policy-isolation-breach.md](runbook-network-policy-isolation-breach.md) | Calico zero-trust network isolation violation diagnosis & quarantine | P1 | `NetworkPolicyViolation` alert |
| [runbook-disaster-recovery-restore.md](runbook-disaster-recovery-restore.md) | Full disaster recovery: Velero backup restore & commit reconstitution | P0 | Regional cluster outage / corruption |
| [azure-teardown-runbook.md](azure-teardown-runbook.md) | 100% leak-free cloud resource teardown & quota reclamation | Operational | Post-drill teardown |
| [portfolio-demo-operations.md](portfolio-demo-operations.md) | Interactive demonstration guide for interviewers | Demo | Technical review sessions |

---

## Incident Response Principles
1. **Preserve Evidence Before Reboot**: Capture pod events, recent logs, and network connection states prior to killing pods.
2. **Deterministic Fallback**: If an upstream dependency (Redis, database) fails, maintain fail-closed or cached fallback state rather than flooding retry queues.
3. **Automated Verification**: Confirm resolution using platform scripts (`measure-sli-baseline.sh`, `test-network-policy-probe.sh`) before resolving incidents.
