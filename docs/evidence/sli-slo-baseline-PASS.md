# Service Level Indicator (SLI) Baseline & Error Budget Calibration

- **Execution Date:** 2026-10-21T15:01:18Z
- **Environment:** Local Platform (`sre-demo-api` on Kubernetes v1.36.1)
- **Status:** **PASS** (Empirical Telemetry Verified)

## 1. Measured SLI Telemetry (Live Prometheus Source)

| Telemetry Metric | Measured Value | Objective / Threshold | Assessment |
|---|:---:|:---:|:---:|
| **Sampled Request Count** | **65** | > 50 requests | **VALID** |
| **Observed 5xx Errors** | **0** | 0 errors under nominal load | **NOMINAL** |
| **Availability SLI** | **100.0000%** | Target SLO: **99.9%** | **PASS** |
| **Latency SLI (p95)** | **< 15ms** | Target SLO: **< 500ms** | **PASS** |

## 2. Multi-Window Multi-Burn-Rate SRE Mathematics

Google SRE defines alert burn rates to eliminate alert fatigue while rapidly catching outages:
85578\text{Burn Rate} = \frac{\text{Observed Error Ratio}}{1 - \text{SLO Target}}85578

Under a **99.9% Availability SLO**, the total allowed error budget is **0.1% (0.001)**:

| Alert Tier | Lookback Windows | Burn Rate Threshold | Budget Consumed | Notification Action |
|---|---|:---:|:---:|---|
| **Page (Fast Burn)** | 5 min & 1 hour | **14.4x** | 2% in 1 hr | PagerDuty / Urgent on-call |
| **Ticket (Slow Burn)** | 30 min & 6 hour | **6.0x** | 5% in 6 hrs | Next-business-day ticket |

- **Empirical Calibration Check:** Under a 5% error injection (5 / 100), the calculated burn rate reaches **50.00x**, accurately triggering the **Fast Burn (14.4x)** alert window while nominal traffic (100.0000%) maintains **0.0x** burn rate.
