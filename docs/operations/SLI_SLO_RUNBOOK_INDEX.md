# Master Operational Matrix: SLI/SLO to Production Runbooks

> **Audited Scope**: `AKS-SRE-Platform` Cloud-Native Runtime  
> **Requirement Reference**: Closes **G16** from the Gap Register.  
> **Standards Alignment**: Google SRE Multiwindow Multi-Burn-Rate Alerting, Calico Zero-Trust, PDB Eviction Safety.

---

## 1. SLI/SLO Target Definitions

| Service / Domain | SLI (Service Level Indicator) | SLO Target | Error Budget (30-day window) | Alert Trigger | Target Runbook |
|---|---|---|---|---|---|
| **API Availability** | Proportion of HTTP requests returning status `< 500` over rolling 30d | **>= 99.90%** | **0.10%** (approx. 43.8 minutes downtime/month) | `SLOHighErrorRateBurn` (Burn Rate >= 14.4x over 5m/1h or >= 6.0x over 30m/6h) | [runbook-sli-slo-error-budget-burn.md](../runbooks/runbook-sli-slo-error-budget-burn.md) |
| **API Latency** | Proportion of successful requests served with `latency <= 200ms` (p95) | **>= 95.00%** | **5.00%** slow requests | `SLOHighLatencyBurn` (p95 > 250ms over 15m) | [runbook-sli-slo-error-budget-burn.md](../runbooks/runbook-sli-slo-error-budget-burn.md) |
| **Zero Downtime Drain** | Proportion of successful requests during rolling node maintenance | **100.00%** | **0%** dropped requests during drain | Node cordon/drain scheduled; `PodDisruptionBudget` violation | [runbook-pdb-node-drain-maintenance.md](../runbooks/runbook-pdb-node-drain-maintenance.md) |
| **Zero-Trust Network Isolation** | Percentage of unauthorized cross-namespace egress/ingress attempts blocked | **100.00%** | **0** permitted unauthorized packets | `NetworkPolicyViolation` alert; unauthorized packet detected | [runbook-network-policy-isolation-breach.md](../runbooks/runbook-network-policy-isolation-breach.md) |
| **Disaster Recovery (RTO / RPO)** | Time to restore cluster state from backup and commit replay | **RTO < 30m, RPO < 5m** | Maximum 5 minutes data delta | Primary region outage / cluster corruption | [runbook-disaster-recovery-restore.md](../runbooks/runbook-disaster-recovery-restore.md) |
| **Cloud Cost & Clean Teardown** | Zero orphaned cloud resources after validation teardown | **100% leak-free** | **$0.00** unintended lingering cost | Post-drill resource auditor flags non-zero vCPU / disk | [azure-teardown-runbook.md](../runbooks/azure-teardown-runbook.md) |

---

## 2. Master Runbook Index

```text
docs/runbooks/
├── README.md                                    # This directory overview & operational conventions
├── runbook-sli-slo-error-budget-burn.md         # P1/P2: Multi-window multi-burn-rate incident remediation
├── runbook-pdb-node-drain-maintenance.md        # P2: Safe node OS upgrades & eviction with PDB
├── runbook-network-policy-isolation-breach.md   # P1: Calico zero-trust policy quarantine & repair
├── runbook-disaster-recovery-restore.md         # P0: Cluster backup restore & state reconstitution
├── azure-teardown-runbook.md                    # Operational: Complete safe cloud teardown & quota release
└── portfolio-demo-operations.md                 # Interactive demonstration guide for interviewers
```

---

## 3. Fast Verification & Triage Commands

### A. Check SLI Baseline & Availability
```bash
bash scripts/measure-sli-baseline.sh
```
*Expected Output:* `Availability SLI: 100%`, `Observed 5xx: 0`, `Burn Rate: 0.0x`.

### B. Execute PDB Drain Maintenance Drill
```bash
bash scripts/pdb-drain-drill.sh
```
*Expected Output:* 0 HTTP errors while active pods are drained and rescheduled to surviving nodes.

### C. Verify Zero-Trust Network Policy Enforcement
```bash
bash scripts/test-network-policy-probe.sh
```
*Expected Output:* 6/6 test cases PASS (4 Negative dropped, 2 Positive allowed).

### D. Verify Infrastructure & Security Gates
```bash
.venv/bin/python tests/test_gates.py
```
*Expected Output:* 17/17 passed.
