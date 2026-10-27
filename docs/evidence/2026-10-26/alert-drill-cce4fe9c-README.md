# Alert fire→resolve drill — 2026-10-26 (aks-portfolio-dev, UTC)

**Result: COMPLETE.** Real Prometheus fire → real Alertmanager receipt → real resolve, all
timestamps UTC, context `aks-portfolio-dev`. Evidence: `alert-drill-cce4fe9c.json`
(repo sha `cce4fe9c2b1d325ab14f1023e77c4996ac5858c9`).

## Why the drill-mock stack, not the capture_aks_alert_cycle.service paths

As recorded in `docs/acceptance/2026-10-26-platform-baseline.md`, this cluster does not yet
run `kube-prometheus-stack` in `monitoring` (no namespace, no PrometheusRule CRD). The repo
scripts hardcode the `monitoring` namespace proxy paths and offer no way to point at another
Prometheus, so neither `alert_drill.sh` (sleep-based, fabricated timestamps — **not** a valid
evidence source) nor `capture_aks_alert_cycle.py`/`alert_drill_simulator.py` could run as-is.

The drill therefore ran against a **real in-cluster Prometheus + Alertmanager** in namespace
`alert-drill` (`prom/prometheus:v2.51.0`, rule evaluation is real; `prom/alertmanager:v0.27.0`),
fixed up from the half-finished mock found there (broken-rule YAML fixed, missing
`prometheus-mock` Service and `alertmanager-mock` Deployment created) and captured by reusing
`capture_aks_alert_cycle.sample()` with the service proxy paths re-pointed to the drill
services (`drill_runner.py` wrapper, kept outside the repo). Labelled in evidence as
`mode: "aks-live drill on in-cluster mock observability stack"`.

## Drill mechanics

- Alert: **`DrillMetricSourceDown`** — `up{job="drill-target"} == 0` for 30s, severity critical.
- Fault injection: `kubectl -n alert-drill scale deployment drill-target --replicas=0`
  (`alert_drill_simulator.py`'s `scale_zero` method; `drill-target` is a drill-owned
  node-exporter target, `flashsale/*` workloads untouched — `opsbridge-api` has an HPA
  with minReplicas=2 that would defeat scale-to-zero anyway).
- Restore: `--replicas=1` right after Alertmanager receipt was observed.

## Timeline (UTC)

| Event | Timestamp (UTC) | Δ from injection |
|---|---|---|
| Baseline verified inactive | 10:12:40.541643Z | — |
| Fault injected (scale drill-target→0) | 10:12:40.541993Z | 0 s |
| Alert fired (Prometheus `state=firing`, activeAt 10:12:47.3066Z) | 10:13:18.636096Z | 38.1 s |
| Alertmanager receipt (`log-receiver`, fingerprint 49e779ea573601d2) | 10:13:24.344628Z | 43.8 s |
| Metric source restored (scale drill-target→1) | 10:13:24.610936Z | 44.1 s |
| Alert resolved (Prometheus `state=inactive`) | 10:13:41.675687Z | 61.1 s |

Fire→resolve: 23.0 s from firing to resolved; injection→resolve 61.1 s;
`notification_delivery_verified: true` = Alertmanager **receipt** (not person-delivery —
same semantics as `capture_aks_alert_cycle.py`, which deliberately sets `false` for
end-user notification).

## Raw evidence

`observations` in `alert-drill-cce4fe9c.json` are verbatim responses of the real Prometheus
`api/v1/rules` and Alertmanager `api/v2/alerts` APIs via the kube API proxy
(`/api/v1/namespaces/alert-drill/services/http:prometheus-mock:9090/proxy/...` and
`.../http:alertmanager-mock-svc:9093/proxy/...`), parsed by the repo's own
`rule_state`/`alertmanager_receivers` functions.

## Cleanup

- `drill-target` restored to 1/1 Ready and left running (its scrape job is part of the
  coherent mock stack). All other flashsale/quanlykho workloads untouched.
- `alert-drill` namespace **kept**: it is not part of gitops manifests (verified — no
  `alert-drill` object in `deploy/` or `gitops/`), but it now holds the consistent mock
  stack used for this and future drills.
- The `alert-log-collector` Deployment (not created in this session; matched to the
  Alertmanager webhook receiver) was crash-looping and was left untouched.
- No git commits/pushes made.
