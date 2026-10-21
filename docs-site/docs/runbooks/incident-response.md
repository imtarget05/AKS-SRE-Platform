# Incident-response demonstration boundary

The current AKS cluster has been deleted. The repository contains a **local
kind alert fire/resolve proof**, not production incident-response SLOs or
contracted P0/P1 response times.

For a local interview walkthrough, use the recorded
[alert cycle](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/evidence/local-platform/l10-observability-PASS.md):
the metric source became unavailable, `LocalPlatformMetricSourceDown` fired,
the source recovered, and the alert resolved. State the environment, timestamps
and what was not measured. The separate
[self-heal record](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/evidence/local-platform/2026-10-21-recreate/selfheal-reverification-2026-10-21.md)
proves two Argo-owned resource recovery cases on kind.

For a real incident, first identify the exact cluster context and affected
service, preserve logs/metrics and timeline, assign an incident owner, and
select the owning workload's rollback or repair runbook. A manual `kubectl
rollout undo` against an Argo-managed resource can be overwritten by GitOps;
the reviewed Git source must express the intended rollback. Azure commands
in the historical teardown runbook are not a routine incident demo.
